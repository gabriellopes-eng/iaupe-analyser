from datetime import datetime

from .client import fetch_html
from .constants import BASE_URL
from .parser import parse_calls
from .policy import resolve_target_year


def collect_calls(url_lista: str = BASE_URL) -> list[tuple[str, datetime | None]]:
    """
    Coleta os editais principais mais recentes da FACEPE como pares
    (url_pdf, data_publicacao).

    O fluxo baixa a pagina de editais abertos, filtra apenas editais principais
    do ano-alvo e ordena por data de publicacao decrescente. A FACEPE transforma
    os blocos em objetos com `publication_date` (extraida de textos como
    "28 de maio de 2026").
    """
    html = fetch_html(url_lista)
    calls = parse_calls(html, target_year=resolve_target_year())
    calls.sort(key=lambda call: (call.publication_date, -call.position), reverse=True)
    return [(call.pdf_url, call.publication_date) for call in calls]


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """So as URLs dos editais principais da FACEPE (sem a data)."""
    return [url for url, _ in collect_calls(url_lista)]
