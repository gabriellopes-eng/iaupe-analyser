from __future__ import annotations

import os
import smtplib
import time
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from .email import Email

# Implementacao concreta de envio.
# Esta classe deixa explicito que o mecanismo usado e SMTP.

# Pasta com os arquivos de imagem dos logos institucionais.
ASSETS_DIR = Path(__file__).parent / "assets"

# Cada logo tem: o Content-ID usado no HTML (ex: <img src="cid:logo_upe">),
# o caminho do arquivo no disco, e o subtipo MIME (jpeg/png) do arquivo.
# Anexados como inline (nao como anexo baixavel) para aparecer direto no corpo do email.
INLINE_LOGOS = (
    ("logo_upe", ASSETS_DIR / "upe_logo_azul.png", "png"),
    ("logo_iit", ASSETS_DIR / "itt_logo.png", "png"),
)

# Pausa entre um envio e o proximo. Um lote de notificacao pode ter centenas de
# docentes; sem pausa, o SMTP do Gmail interpreta a rajada de logins/mensagens
# como abuso e derruba a conexao ("Connection unexpectedly closed"), fazendo
# todos os envios seguintes falharem. 1s por mensagem mantem o ritmo abaixo do
# limite de rate e ainda cabe num job de CI (300 e-mails ~= 5 min).
SMTP_SEND_DELAY_SECONDS = float((os.getenv("SMTP_SEND_DELAY_SECONDS") or "1.0").strip())


class SmtpEmailService:
    """Implementacao concreta de envio de email via SMTP com STARTTLS.

    Mantem UMA conexao aberta e reaproveitada entre envios (em vez de conectar +
    logar a cada mensagem). Isso e o que permite mandar um lote grande de
    notificacoes sem o servidor cortar a conexao. A conexao e reaberta sozinha
    se cair no meio do lote, entao a falha de uma mensagem nao derruba as
    seguintes. Chame `close()` ao terminar o lote (ou use como context manager).
    """

    def __init__(self) -> None:
        # Carrega as configuracoes do ambiente para evitar credenciais no codigo.
        load_dotenv(override=True)

        # Host/porta do servidor SMTP.
        self.host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
        self.port = int((os.getenv("SMTP_PORT") or "587").strip())

        # Credenciais de autenticacao.
        self.user = (os.getenv("SMTP_USER") or "").strip()
        self.password = (os.getenv("SMTP_PASS") or "").strip()

        # Remetente padrao usado no header From.
        self.default_from = (os.getenv("SENDER_EMAIL") or self.user).strip()

        if not self.user:
            raise ValueError("Defina SMTP_USER no .env")
        if not self.password:
            raise ValueError("Defina SMTP_PASS no .env")

        # Conexao viva, criada sob demanda no primeiro envio.
        self._smtp: smtplib.SMTP | None = None

    def __enter__(self) -> "SmtpEmailService":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _connect(self) -> smtplib.SMTP:
        """Abre uma conexao nova: TLS + autenticacao."""
        smtp = smtplib.SMTP(self.host, self.port, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(self.user, self.password)
        return smtp

    def _ensure_connection(self) -> smtplib.SMTP:
        """Devolve uma conexao viva, reaproveitando a atual ou reabrindo."""
        if self._smtp is not None:
            try:
                # NOOP barato so pra confirmar que o servidor ainda responde.
                if self._smtp.noop()[0] == 250:
                    return self._smtp
            except smtplib.SMTPException:
                pass
            self.close()

        self._smtp = self._connect()
        return self._smtp

    def close(self) -> None:
        """Fecha a conexao SMTP, se houver. Seguro chamar varias vezes."""
        if self._smtp is not None:
            try:
                self._smtp.quit()
            except Exception:
                pass
            self._smtp = None

    def send(self, email: Email) -> None:
        """Envia um unico email com destinatarios em copia (Cc)."""
        # Se houver HTML, a notificacao vai formatada; caso contrario, cai para texto puro.
        body_text = (email.text or "").strip()
        body_html = (email.html or "").strip()
        body = body_html if body_html else body_text
        content_subtype = "html" if body_html else "plain"

        if not body:
            raise ValueError("Informe text ou html para envio")

        # O campo email.to aceita lista separada por virgula.
        cc_recipients = [part.strip() for part in email.to.split(",") if part.strip()]
        if not cc_recipients:
            raise ValueError("Informe ao menos um destinatario valido em Email.to")

        # Mantemos um unico destinatario no To e todos os alvos reais em Cc.
        to_header = self.default_from

        # multipart/related e o tipo de mensagem que permite um corpo HTML referenciar
        # imagens anexadas na propria mensagem via "cid:", em vez de depender de uma URL
        # externa (que muitos clientes de email bloqueiam por padrao).
        message = MIMEMultipart("related")
        message["From"] = self.default_from
        message["To"] = to_header
        message["Cc"] = ", ".join(cc_recipients)
        message["Subject"] = email.subject
        # O corpo (texto ou HTML) sempre entra como a primeira parte da mensagem.
        message.attach(MIMEText(body, content_subtype, "utf-8"))

        if content_subtype == "html":
            # So anexa cada logo se o HTML realmente referencia o Content-ID dele
            # (evita anexar imagem em templates que nao usam logo) e se o arquivo existe.
            for content_id, path, subtype in INLINE_LOGOS:
                if content_id not in body or not path.exists():
                    continue
                logo = MIMEImage(path.read_bytes(), _subtype=subtype)
                # Content-ID e o que liga o anexo ao "cid:logo_upe" usado no <img src>.
                logo.add_header("Content-ID", f"<{content_id}>")
                # "inline" (em vez de "attachment") faz o cliente de email exibir a
                # imagem no corpo da mensagem, sem listar como anexo separado.
                logo.add_header("Content-Disposition", "inline", filename=path.name)
                message.attach(logo)

        payload = message.as_bytes()

        # Duas tentativas: se a conexao reaproveitada tiver morrido bem na hora do
        # envio, a 1a falha, reabrimos e a 2a vai numa conexao limpa. So depois
        # disso o erro sobe para o chamador (que registra a falha e segue pro
        # proximo destinatario).
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                smtp = self._ensure_connection()
                smtp.sendmail(self.default_from, cc_recipients, payload)
                last_exc = None
                break
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPException, OSError) as exc:
                last_exc = exc
                self.close()

        # Espaca o proximo envio mesmo quando este falhou: se o servidor esta
        # reclamando de ritmo, insistir mais rapido so piora.
        if SMTP_SEND_DELAY_SECONDS > 0:
            time.sleep(SMTP_SEND_DELAY_SECONDS)

        if last_exc is not None:
            raise last_exc
