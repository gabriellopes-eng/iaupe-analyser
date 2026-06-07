from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .client import fetch_html
from .constants import BASE_URL
from .models import CapesDocument
from .parser import collect_open_call_pages, parse_documents_from_program_page
from .policy import resolve_target_year


def collect_documents(url_lista: str = BASE_URL) -> list[CapesDocument]:
    """Coleta editais principais da CAPES como objetos ordenaveis."""
    try:
        html = fetch_html(url_lista)
    except requests.RequestException as exc:
        print(f"Erro ao acessar CAPES: {exc}")
        return []

    soup = BeautifulSoup(html, "lxml")
    is_index = "/editais-e-resultados-capes" in (urlparse(url_lista).path or "")
    program_pages = collect_open_call_pages(url_lista, soup) if is_index else [url_lista]
    target_year = resolve_target_year()

    documents: list[CapesDocument] = []
    seen: set[str] = set()

    for page_url in program_pages:
        try:
            page_html = fetch_html(page_url)
        except requests.RequestException as exc:
            print(f"[CAPES] Subpagina ignorada por erro HTTP: {page_url} | {exc}")
            continue

        for document in parse_documents_from_program_page(
            page_url=page_url,
            html=page_html,
            target_year=target_year,
        ):
            if document.pdf_url in seen:
                continue

            seen.add(document.pdf_url)
            documents.append(document)

    return documents


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """Coleta URLs dos editais principais mais recentes da CAPES."""
    return [document.pdf_url for document in collect_documents(url_lista)]
