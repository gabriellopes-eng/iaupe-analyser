from __future__ import annotations

from datetime import date, datetime


def format_ptbr_date(value: object, fallback: str = "N/A") -> str:
    """Formata datas como dd/mm/aaaa para exibicao em e-mails."""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    raw = str(value or "").strip()
    if not raw:
        return fallback

    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).strftime("%d/%m/%Y")
        except ValueError:
            pass

    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return raw
