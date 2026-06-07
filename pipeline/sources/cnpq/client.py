import requests

from .constants import REQUEST_HEADERS


def fetch_html(url: str) -> str:
    """Baixa uma pagina HTML do CNPq."""
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_html_or_empty(url: str) -> str:
    """Baixa HTML do CNPq sem derrubar o scraper quando uma pagina falha."""
    try:
        return fetch_html(url)
    except requests.RequestException as exc:
        print(f"Erro ao abrir detalhe da chamada CNPq: {exc}")
        return ""
