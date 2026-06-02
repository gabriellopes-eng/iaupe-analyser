from __future__ import annotations

import base64
import os
from datetime import datetime
from html import escape
from pathlib import Path

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

    def resolve_edital_titulo(self, saved_json: dict) -> str:
        titulo = str(saved_json.get("titulo") or saved_json.get("titulo_edital") or "").strip()
        if not titulo:
            titulo = str(saved_json.get("descricao") or "").strip()
        return titulo or "Edital sem titulo identificado"

    def resolve_logo_data_uri(self) -> str:
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
        if not logo_path.exists():
            return ""
        try:
            encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        except OSError:
            return ""

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
        edital_titulo = escape(self.resolve_edital_titulo(saved_json))
        logo_src = self.resolve_logo_data_uri()
        descricao = escape(str(saved_json.get("descricao") or "Nao informado"))
        publico_alvo = escape(str(saved_json.get("publico_alvo") or "Nao informado"))
        data_limite = escape(deadline.date().isoformat())
        safe_url = escape(pdf_url)

        return (
            "<html lang='pt-BR'>"
            "<head>"
            "<meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            "<title>Alerta de Prazo</title>"
            "<link href='https://fonts.googleapis.com/css?family=Montserrat:400,600,700&display=swap' rel='stylesheet'>"
            "</head>"
            "<body style=\"margin:0; padding:0; background-color:#dce8f5; font-family:'Montserrat',Arial,sans-serif; color:#1a1a2e;\">"
            "<table width='100%' cellpadding='0' cellspacing='0' border='0' style='background:#dce8f5; padding:32px 16px;'>"
            "<tr><td align='center'>"
            "<table width='620' cellpadding='0' cellspacing='0' border='0' style='max-width:620px; width:100%;'>"
            "<tr><td style='background:linear-gradient(90deg,#e67e22 0%,#c0392b 100%); height:5px; border-radius:8px 8px 0 0;'></td></tr>"
            "<tr><td style='background:linear-gradient(135deg,#1a3a6b 0%,#2a5298 100%); padding:28px 36px 24px;'>"
            "<table width='100%'><tr>"
            "<td valign='middle'>"
            "<p style='margin:0 0 2px; font-size:10px; letter-spacing:3px; text-transform:uppercase; color:#a8c4e8; font-weight:600;'>Plataforma de Monitoramento de Editais</p>"
            f"<h1 style='margin:0; font-family:Montserrat,Arial,sans-serif; font-size:22px; font-weight:600; color:#fff; line-height:1.3;'>{edital_titulo}</h1>"
            "</td>"
            f"<td align='right' valign='middle' style='padding-left:20px; min-width:140px;'><img src='{logo_src}' alt='IAUPE' height='48' style='display:block; filter:brightness(0) invert(1);'></td>"
            "</tr></table>"
            "</td></tr>"
            "<tr><td style='background:#2a5298; padding:14px 36px; border-bottom:2px solid #e67e22;'>"
            "<table width='100%'><tr>"
            f"<td><span style='font-size:13px; color:#a8c4e8;'>Instituição: </span><span style='font-size:14px; font-weight:700; color:#fff;'>{escape(source_label)}</span></td>"
            f"<td align='right'><span style='font-family:Courier New,monospace; font-size:11px; color:#a8c4e8; background:#1a3a6b; padding:4px 10px; border-radius:3px;'>Ref: {escape(source_id)}</span></td>"
            "</tr></table>"
            "</td></tr>"
            "<tr><td style='background:linear-gradient(135deg,#e67e22 0%,#c0392b 100%); padding:20px 36px;'>"
            "<table width='100%'><tr valign='middle'>"
            "<td>"
            "<p style='margin:0 0 2px; font-size:11px; letter-spacing:2px; text-transform:uppercase; color:rgba(255,255,255,0.8); font-weight:600;'>Alerta de Prazo</p>"
            f"<p style='margin:0; font-size:26px; font-weight:700; color:#fff; font-family:Montserrat,Arial,sans-serif;'>Faltam <span style='background:rgba(0,0,0,0.2); padding:2px 12px; border-radius:4px;'>{days_left} dia(s)</span></p>"
            "</td>"
            "<td align='right'>"
            "<p style='margin:0; font-size:10px; color:rgba(255,255,255,0.7); text-transform:uppercase; letter-spacing:1.5px;'>Prazo final</p>"
            f"<p style='margin:4px 0 0; font-size:20px; font-weight:700; color:#fff;'>{data_limite}</p>"
            "</td>"
            "</tr></table>"
            "</td></tr>"
            "<tr><td style='background:#ffffff; padding:0;'>"
            "<div style='padding:24px 36px; border-bottom:1px solid #eaf1fb;'>"
            "<p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Público-alvo</p>"
            f"<p style='margin:0; font-size:14px; line-height:1.75; color:#2d3748;'>{publico_alvo}</p>"
            "</div>"
            "<div style='padding:24px 36px; border-bottom:1px solid #eaf1fb;'>"
            "<p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Resumo do Edital</p>"
            f"<p style='margin:0; font-size:14px; line-height:1.75; color:#2d3748;'>{descricao}</p>"
            "</div>"
            "<div style='padding:20px 36px;'>"
            "<p style='margin:0 0 8px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Documento oficial</p>"
            f"<a href='{safe_url}' style='font-size:14px; font-weight:700; color:#2a5298; text-decoration:none;'>Acessar edital em PDF</a>"
            "</div>"
            "</td></tr>"
            "<tr><td style='background:#eaf1fb; padding:28px 36px; text-align:center; border-top:2px solid #e67e22;'>"
            f"<a href='{safe_url}' style='display:inline-block; background:linear-gradient(135deg,#e67e22,#c0392b); color:#fff; font-size:13px; font-weight:700; letter-spacing:1px; text-transform:uppercase; text-decoration:none; padding:14px 44px; border-radius:3px; box-shadow:0 3px 10px rgba(192,57,43,0.35);'>Submeter Proposta Agora</a>"
            "</td></tr>"
            "<tr><td style='background:#1a3a6b; border-radius:0 0 8px 8px; padding:20px 36px; text-align:center;'>"
            "<p style='margin:0; font-size:11px; color:#7a9cc8; line-height:1.7;'>Este e-mail foi gerado automaticamente pela plataforma de monitoramento de editais.<br>"
            "Você está recebendo esta mensagem porque está cadastrado para receber alertas de oportunidades.</p>"
            "</td></tr>"
            "</table></td></tr></table>"
            "</body></html>"
        )
