from __future__ import annotations

import os
import smtplib

from dotenv import load_dotenv

from .email import Email

# Implementacao concreta de envio.
# Esta classe deixa explicito que o mecanismo usado e SMTP.


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
        content_type = "text/html" if body_html else "text/plain"

        if not body:
            raise ValueError("Informe text ou html para envio")

        # O campo email.to aceita lista separada por virgula.
        cc_recipients = [part.strip() for part in email.to.split(",") if part.strip()]
        if not cc_recipients:
            raise ValueError("Informe ao menos um destinatario valido em Email.to")

        # Mantemos um unico destinatario no To e todos os alvos reais em Cc.
        to_header = self.default_from

        # Monta a mensagem SMTP com headers minimos e o corpo final.
        message = "\r\n".join([
            f"From: {self.default_from}",
            f"To: {to_header}",
            f"Cc: {', '.join(cc_recipients)}",
            f"Subject: {email.subject}",
            "MIME-Version: 1.0",
            f"Content-Type: {content_type}; charset=utf-8",
            "",
            body,
        ])

        # Fluxo do envio:
        # conecta, sobe TLS, autentica e despacha a mensagem.
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.user, self.password)
            smtp.sendmail(self.default_from, cc_recipients, message.encode("utf-8"))