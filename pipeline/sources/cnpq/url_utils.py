import re
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

from .constants import URL_REGEX


def normalize_url(url: str) -> str:
    """Normaliza URLs do CNPq removendo barras extras em parametros conhecidos."""
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return (url or "").strip()

    normalized_path = parsed.path
    if parsed.query and normalized_path.endswith("/") and len(normalized_path) > 1:
        normalized_path = normalized_path.rstrip("/")

    normalized_query = re.sub(r"(idDivulgacao=\d+)/", r"\1", parsed.query or "")
    return parsed._replace(path=normalized_path, query=normalized_query).geturl()


def is_cnpq_domain(url: str) -> bool:
    """Confere se a URL pertence a um dominio aceito do ecossistema CNPq."""
    host = (urlparse(url).netloc or "").lower()
    return any(
        domain in host
        for domain in (
            "memoria2.cnpq.br",
            "cnpq.br",
            "resultado.cnpq.br",
            "efomento.cnpq.br",
        )
    )


def is_pdf_url(url: str) -> bool:
    """Identifica URLs que apontam diretamente para PDF."""
    path = (urlparse(url).path or "").lower()
    return path.endswith(".pdf")


def is_detail_page(url: str) -> bool:
    """Identifica paginas de detalhe de chamadas divulgadas do CNPq."""
    parsed = urlparse(url)
    query = (parsed.query or "").lower()
    return (
        "memoria2.cnpq.br" in (parsed.netloc or "").lower()
        and (
            "iddisvulgacao=" in query
            or "iddivulgacao=" in query
            or "detalha=chamadadivulgada" in query
        )
    )


def extract_embedded_urls(value: str) -> list[str]:
    """Extrai URLs embutidas em parametros de share/mailto."""
    decoded = value or ""
    for _ in range(2):
        decoded = unquote(decoded)

    urls: list[str] = []
    for match in URL_REGEX.findall(decoded):
        cleaned = match.rstrip(".,;)")
        if cleaned:
            urls.append(cleaned)
    return urls


def expand_href_candidates(page_url: str, href: str) -> list[str]:
    """Expande um href em possiveis URLs reais, incluindo URLs embutidas."""
    full_href = normalize_url(urljoin(page_url, href))
    candidates: list[str] = [full_href]

    parsed = urlparse(full_href)
    for _, value in parse_qsl(parsed.query or "", keep_blank_values=True):
        for embedded in extract_embedded_urls(value):
            candidates.append(normalize_url(embedded))

    if parsed.scheme.lower() == "mailto":
        for embedded in extract_embedded_urls(full_href):
            candidates.append(normalize_url(embedded))

    seen: set[str] = set()
    deduped: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
