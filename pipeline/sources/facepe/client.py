import requests

from .constants import REQUEST_HEADERS


def fetch_html(url: str) -> str:
    """Baixa a pagina HTML de editais da FACEPE."""
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text
