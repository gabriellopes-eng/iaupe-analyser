import requests

from .client import fetch_html, fetch_html_or_empty
from .constants import BASE_URL
from .parser import extract_anchor_candidates, extract_pdf_links_from_detail, parse_open_calls
from .url_utils import is_cnpq_domain, is_detail_page, is_pdf_url


def sort_open_call_urls(html: str, page_url: str) -> list[str]:
    """Ordena chamadas abertas pela data inicial de inscricao mais recente."""
    calls = parse_open_calls(html, page_url)
    calls.sort(
        key=lambda call: (
            call.inscription_start_date is not None,
            call.inscription_start_date,
            -call.position,
        ),
        reverse=True,
    )
    return [call.detail_url for call in calls]


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """Coleta links de chamadas publicas abertas a partir da pagina do CNPq."""
    try:
        html = fetch_html(url_lista)
    except requests.RequestException as exc:
        print(f"Erro ao acessar CNPq: {exc}")
        return []

    links: list[str] = []
    seen_links: set[str] = set()
    detail_pages: list[str] = sort_open_call_urls(html, url_lista)
    seen_details: set[str] = set(detail_pages)

    for candidate in extract_anchor_candidates(html, url_lista):
        if not is_cnpq_domain(candidate):
            continue

        if is_pdf_url(candidate):
            if candidate not in seen_links:
                seen_links.add(candidate)
                links.append(candidate)
            continue

        if is_detail_page(candidate) and candidate not in seen_details:
            seen_details.add(candidate)
            detail_pages.append(candidate)

    for detail_url in detail_pages:
        detail_html = fetch_html_or_empty(detail_url)
        for pdf_link in extract_pdf_links_from_detail(detail_html, detail_url):
            if pdf_link not in seen_links:
                seen_links.add(pdf_link)
                links.append(pdf_link)

    if not links and detail_pages:
        return detail_pages

    return links
