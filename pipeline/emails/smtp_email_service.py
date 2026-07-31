from __future__ import annotations

import os
import smtplib
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


class SmtpEmailService:
    """Implementacao concreta de envio de email via SMTP com STARTTLS."""

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

        # Fluxo do envio:
        # conecta, sobe TLS, autentica e despacha a mensagem.
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.user, self.password)
            smtp.sendmail(self.default_from, cc_recipients, message.as_bytes())