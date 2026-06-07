from time import sleep
from urllib.parse import urlparse

import requests

from .constants import REQUEST_ATTEMPTS, REQUEST_HEADERS, REQUEST_TIMEOUT


def build_fallback_urls(url: str) -> list[str]:
    """Gera variantes www.gov.br/gov.br para reduzir falhas por redirecionamento."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()

    candidates = [url]
    if host == "www.gov.br":
        candidates.append(url.replace("https://www.gov.br", "https://gov.br", 1))
    elif host == "gov.br":
        candidates.append(url.replace("https://gov.br", "https://www.gov.br", 1))

    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def get_with_retry(url: str) -> requests.Response:
    """Executa GET com tentativas e fallback de host."""
    last_exc: requests.RequestException | None = None

    for candidate in build_fallback_urls(url):
        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            try:
                response = requests.get(
                    candidate,
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < REQUEST_ATTEMPTS:
                    sleep(attempt)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Falha inesperada ao requisitar URL")


def fetch_html(url: str) -> str:
    """Baixa uma pagina HTML da CAPES."""
    return get_with_retry(url).text
