from __future__ import annotations

import os
from datetime import datetime
from html import escape

from dotenv import load_dotenv

from .send_email_use_case import SendEmailUseCase
from .smtp_email_service import SmtpEmailService


class DeadlineReminderEmailNotifier:
    """Envia notificacao de prazo de submissao (D-30, D-15, D-7)."""

    def __init__(self, test_recipient: str | None = None) -> None:
        load_dotenv(override=True)
        self.test_recipient = (test_recipient or os.getenv("RECIPIENT_EMAIL") or "").strip()
        self._use_case: SendEmailUseCase | None = None

    def is_enabled(self) -> bool:
        return bool(self.test_recipient)

    def notify_deadline(
        self,
        *,
        source_label: str,
        source_id: str,
        pdf_url: str,
        saved_json: dict,
        deadline: datetime,
        days_left: int,
    ) -> None:
        if not self.is_enabled():
            return

        if self._use_case is None:
            self._use_case = SendEmailUseCase(SmtpEmailService())

        subject = (
            f"[IAUPE] Prazo de submissao em {days_left} dia(s) - "
            f"{source_label} ({source_id})"
        )
        html = self.build_html(
            source_label=source_label,
            source_id=source_id,
            pdf_url=pdf_url,
            saved_json=saved_json,
            deadline=deadline,
            days_left=days_left,
        )

        self._use_case.execute(
            {
                "to": self.test_recipient,
                "subject": subject,
                "html": html,
            }
        )

    def build_html(
        self,
        *,
        source_label: str,
        source_id: str,
        pdf_url: str,
        saved_json: dict,
        deadline: datetime,
        days_left: int,
    ) -> str:
        descricao = escape(str(saved_json.get("descricao") or "Nao informado"))
        publico_alvo = escape(str(saved_json.get("publico_alvo") or "Nao informado"))
        data_limite = escape(deadline.date().isoformat())
        safe_url = escape(pdf_url)

        return (
            "<html><body style='font-family:Arial,sans-serif; line-height:1.5;'>"
            f"<h2>Prazo proximo do fim: faltam {days_left} dia(s)</h2>"
            f"<p><b>Fonte:</b> {escape(source_label)} ({escape(source_id)})</p>"
            f"<p><b>Data limite de submissao:</b> {data_limite}</p>"
            f"<p><b>Publico-alvo:</b> {publico_alvo}</p>"
            f"<p><b>Resumo:</b> {descricao}</p>"
            f"<p><a href='{safe_url}'>Acessar edital em PDF</a></p>"
            "</body></html>"
        )
