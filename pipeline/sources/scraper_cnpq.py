import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

SOURCE_KEY = "cnpq"
SOURCE_LABEL = "CNPq"
BASE_URL = (
    "http://memoria2.cnpq.br/web/guest/chamadas-publicas"
    "?p_p_id=resultadosportlet_WAR_resultadoscnpqportlet_INSTANCE_0ZaM"
    "&filtro=abertas"
)
MONGO_COLLECTION = "editais_cnpq"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
URL_REGEX = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
DATE_REGEX = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")


def normalize_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return (url or "").strip()

    normalized_path = parsed.path
    if parsed.query and normalized_path.endswith("/") and len(normalized_path) > 1:
        normalized_path = normalized_path.rstrip("/")

    normalized_query = re.sub(r"(idDivulgacao=\d+)/", r"\1", parsed.query or "")
    normalized = parsed._replace(path=normalized_path, query=normalized_query).geturl()
    return normalized


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


def parse_ptbr_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return None


def extract_inscription_start_date(item) -> datetime | None:
    inscricao = item.select_one(".inscricao")
    if inscricao is None:
        return None

    match = DATE_REGEX.search(inscricao.get_text(" ", strip=True))
    if not match:
        return None

    return parse_ptbr_date(match.group(1))


def extract_permanent_link(item, page_url: str) -> str:
    permanent_input = item.select_one(".link-permanente input[value]")
    if permanent_input is not None:
        value = str(permanent_input.get("value") or "").strip()
        if value:
            return normalize_url(urljoin(page_url, value))

    for anchor in item.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        for candidate in expand_href_candidates(page_url, href):
            if is_detail_page(candidate):
                return candidate

    return ""


def collect_sorted_detail_pages(soup: BeautifulSoup, page_url: str) -> list[str]:
    calls: list[tuple[datetime | None, int, str]] = []
    seen: set[str] = set()

    for index, item in enumerate(soup.select("ol.list-chamadas > li")):
        detail_url = extract_permanent_link(item, page_url)
        if not detail_url or detail_url in seen:
            continue

        seen.add(detail_url)
        calls.append((extract_inscription_start_date(item), index, detail_url))

    # Prioriza chamadas com data conhecida, da inscricao mais recente para a mais antiga.
    calls.sort(
        key=lambda row: (row[0] is not None, row[0] or datetime.min, -row[1]),
        reverse=True,
    )
    return [detail_url for _, _, detail_url in calls]


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


def extract_embedded_urls(value: str) -> list[str]:
    decoded = value or ""
    # URLs da chamada podem vir codificadas mais de uma vez em parametros de share.
    for _ in range(2):
        decoded = unquote(decoded)

    urls: list[str] = []
    for match in URL_REGEX.findall(decoded):
        cleaned = match.rstrip(".,;)")
        if cleaned:
            urls.append(cleaned)
    return urls


def expand_href_candidates(url_lista: str, href: str) -> list[str]:
    full_href = normalize_url(urljoin(url_lista, href))
    candidates: list[str] = [full_href]

    parsed = urlparse(full_href)
    for _, value in parse_qsl(parsed.query or "", keep_blank_values=True):
        for embedded in extract_embedded_urls(value):
            candidates.append(normalize_url(embedded))

    if parsed.scheme.lower() == "mailto":
        for embedded in extract_embedded_urls(full_href):
            candidates.append(normalize_url(embedded))

    # preserva ordem de descoberta e remove duplicados
    seen: set[str] = set()
    deduped: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


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
    detail_pages: list[str] = collect_sorted_detail_pages(soup, url_lista)
    detail_seen: set[str] = set(detail_pages)

    # seletor principal da estrutura atual do site
    anchors = soup.select("div.links-normas.pull-left a.btn[href]")

    # fallback defensivo caso o HTML mude levemente
    if not anchors:
        anchors = soup.select("a[href]")

    for a in anchors:
        href = (a.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        for candidate in expand_href_candidates(url_lista, href):
            if not is_cnpq_domain(candidate):
                continue

            if is_pdf_url(candidate):
                if candidate not in vistos:
                    vistos.add(candidate)
                    links.append(candidate)
                continue

            if is_detail_page(candidate) and candidate not in detail_seen:
                detail_seen.add(candidate)
                detail_pages.append(candidate)

    for detail_url in detail_pages:
        for pdf_link in extract_pdf_links_from_detail(detail_url):
            if pdf_link not in vistos:
                vistos.add(pdf_link)
                links.append(pdf_link)

    if not links and detail_pages:
        # fallback para nao perder chamadas quando o PDF nao estiver explicito no HTML de detalhe
        return detail_pages

    return links
