import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SOURCE_KEY = "cnpq"
SOURCE_LABEL = "CNPq"
BASE_URL = "http://memoria2.cnpq.br/web/guest/chamadas-publicas"
MONGO_COLLECTION = "editais_cnpq"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}


def is_cnpq_domain(url: str) -> bool:
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
    path = (urlparse(url).path or "").lower()
    return path.endswith(".pdf")


def is_detail_page(url: str) -> bool:
    parsed = urlparse(url)
    query = (parsed.query or "").lower()
    return (
        "memoria2.cnpq.br" in (parsed.netloc or "").lower()
        and ("iddisvulgacao=" in query or "iddivulgacao=" in query or "detalha=chamadadivulgada" in query)
    )


def extract_pdf_links_from_detail(detail_url: str) -> list[str]:
    try:
        resp = requests.get(detail_url, headers=REQUEST_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Erro ao abrir detalhe da chamada CNPq: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    pdf_links: list[str] = []
    seen: set[str] = set()

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        full_href = urljoin(detail_url, href)
        if not is_pdf_url(full_href):
            continue

        if full_href not in seen:
            seen.add(full_href)
            pdf_links.append(full_href)

    return pdf_links


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """Coleta links de chamadas publicas a partir da pagina do CNPq."""
    try:
        resp = requests.get(
            url_lista,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Erro ao acessar CNPq: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    links: list[str] = []
    vistos: set[str] = set()
    detail_pages: list[str] = []
    detail_seen: set[str] = set()

    # seletor principal da estrutura atual do site
    anchors = soup.select("div.links-normas.pull-left a.btn[href]")

    # fallback defensivo caso o HTML mude levemente
    if not anchors:
        anchors = soup.select("a[href]")

    for a in anchors:
        href = (a.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        full_href = urljoin(url_lista, href)
        if not is_cnpq_domain(full_href):
            continue

        if is_pdf_url(full_href):
            if full_href not in vistos:
                vistos.add(full_href)
                links.append(full_href)
            continue

        if is_detail_page(full_href) and full_href not in detail_seen:
            detail_seen.add(full_href)
            detail_pages.append(full_href)

    for detail_url in detail_pages:
        for pdf_link in extract_pdf_links_from_detail(detail_url):
            if pdf_link not in vistos:
                vistos.add(pdf_link)
                links.append(pdf_link)

    if not links and detail_pages:
        # fallback para nao perder chamadas quando o PDF nao estiver explicito no HTML de detalhe
        return detail_pages

    return links