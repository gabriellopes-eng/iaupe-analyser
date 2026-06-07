from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import DATE_REGEX
from .models import CnpqCall
from .url_utils import expand_href_candidates, is_detail_page, is_pdf_url, normalize_url


def parse_ptbr_date(value: str) -> datetime | None:
    """Converte datas dd/mm/YYYY para datetime."""
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return None


def extract_inscription_start_date(item) -> datetime | None:
    """Extrai a data inicial de inscricao de um card de chamada do CNPq."""
    inscricao = item.select_one(".inscricao")
    if inscricao is None:
        return None

    match = DATE_REGEX.search(inscricao.get_text(" ", strip=True))
    if not match:
        return None

    return parse_ptbr_date(match.group(1))


def extract_permanent_link(item, page_url: str) -> str:
    """Extrai o link permanente da chamada a partir do card do CNPq."""
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


def parse_open_calls(html: str, page_url: str) -> list[CnpqCall]:
    """Transforma a pagina de chamadas abertas em chamadas ordenaveis."""
    soup = BeautifulSoup(html, "lxml")
    calls: list[CnpqCall] = []
    seen: set[str] = set()

    for position, item in enumerate(soup.select("ol.list-chamadas > li")):
        detail_url = extract_permanent_link(item, page_url)
        if not detail_url or detail_url in seen:
            continue

        seen.add(detail_url)
        calls.append(
            CnpqCall(
                detail_url=detail_url,
                position=position,
                inscription_start_date=extract_inscription_start_date(item),
            )
        )

    return calls


def extract_anchor_candidates(html: str, page_url: str) -> list[str]:
    """Coleta URLs de PDFs ou paginas de detalhe em anchors da pagina."""
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.select("div.links-normas.pull-left a.btn[href]")
    if not anchors:
        anchors = soup.select("a[href]")

    candidates: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        href = str(anchor.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        for candidate in expand_href_candidates(page_url, href):
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

    return candidates


def extract_pdf_links_from_detail(html: str, detail_url: str) -> list[str]:
    """Extrai PDFs de uma pagina de detalhe do CNPq."""
    soup = BeautifulSoup(html, "lxml")
    pdf_links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        full_href = urljoin(detail_url, href)
        if not is_pdf_url(full_href) or full_href in seen:
            continue

        seen.add(full_href)
        pdf_links.append(full_href)

    return pdf_links
