from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .models import CapesDocument
from .policy import is_pdf_url, is_primary_edital, is_target_year_document
from .text_utils import clean_href


def parse_ptbr_date(value: str) -> datetime | None:
    """Converte datas dd/mm/YYYY da tabela da CAPES para datetime."""
    try:
        return datetime.strptime((value or "").strip(), "%d/%m/%Y")
    except ValueError:
        return None


def find_heading(soup: BeautifulSoup, title: str):
    """Procura heading h2/h3/h4 com texto exato."""
    wanted = title.strip().lower()
    return soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(" ", strip=True).strip().lower() == wanted
    )


def collect_open_call_pages(index_url: str, soup: BeautifulSoup) -> list[str]:
    """Coleta subpaginas listadas na secao Editais Abertos da pagina indice."""
    heading = find_heading(soup, "Editais Abertos")
    if not heading:
        return []

    container = heading.find_next(["ul", "ol"])
    if not container:
        return []

    pages: list[str] = []
    seen: set[str] = set()

    for item in container.find_all("li", recursive=False):
        anchor = item.find("a", class_="external-link", href=True) or item.find("a", href=True)
        if not anchor:
            continue

        href = clean_href(anchor.get("href") or "")
        if not href:
            continue

        full_url = urljoin(index_url, href)
        parsed = urlparse(full_url)
        if (parsed.netloc or "").lower() != "www.gov.br":
            continue
        if "/capes/" not in (parsed.path or ""):
            continue

        if full_url not in seen:
            seen.add(full_url)
            pages.append(full_url)

    return pages


def find_editais_table(soup: BeautifulSoup):
    """Localiza a tabela de documentos da secao Editais.

    Nao filtra por classe CSS: o gov.br ja trocou o nome da classe da tabela
    pelo menos uma vez (de "listing" para "slate-table-block", gerada pelo
    editor de blocos), o que zerava a coleta silenciosamente. A primeira
    tabela apos o heading "Editais" e a que importa, independente da classe.
    """
    heading = find_heading(soup, "Editais")
    if heading is not None:
        table = heading.find_next("table")
        if table is not None:
            return table

    return soup.select_one("table.arquivos.listing") or soup.select_one("table.listing")


def extract_first_pdf_url(row, page_url: str) -> str:
    """Extrai o primeiro PDF valido de uma linha de tabela."""
    for anchor in row.select("a[href]"):
        href = clean_href(anchor.get("href") or "")
        if not href:
            continue

        full_url = clean_href(urljoin(page_url, href))
        if is_pdf_url(full_url):
            return full_url

    return ""


def parse_documents_from_program_page(
    *,
    page_url: str,
    html: str,
    target_year: int,
) -> list[CapesDocument]:
    """Transforma a tabela de uma subpagina da CAPES em editais principais.
    O parser filtra documentos por data, ano-alvo e se são editais principais aqui.
    
    Ponto importante para apresentar com precisão: 
    diferente de FACEPE e CNPq, a CAPES não tem um sort() explícito no código atual. 
    Ela segue a ordem oficial da seção “Editais Abertos” no site, depois filtra os documentos válidos.
    
    """
    soup = BeautifulSoup(html, "lxml")
    table = find_editais_table(soup)
    if table is None:
        return []

    documents: list[CapesDocument] = []
    seen: set[str] = set()

    for position, row in enumerate(table.select("tr")):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        publication_date = parse_ptbr_date(cells[0].get_text(" ", strip=True))
        title = cells[1].get_text(" ", strip=True)
        pdf_url = extract_first_pdf_url(row, page_url)

        if publication_date is None or publication_date.year != target_year:
            continue
        if not pdf_url or pdf_url in seen:
            continue
        if not is_target_year_document(title, pdf_url, target_year):
            continue
        if not is_primary_edital(title, target_year):
            continue

        seen.add(pdf_url)
        documents.append(
            CapesDocument(
                title=title,
                pdf_url=pdf_url,
                publication_date=publication_date,
                source_page_url=page_url,
                position=position,
            )
        )

    return documents
