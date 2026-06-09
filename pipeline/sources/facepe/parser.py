import re
from datetime import datetime

from bs4 import BeautifulSoup

from .constants import MONTHS
from .models import FacepeCall
from .policy import is_primary_edital
from .text_utils import normalize_text

DATE_REGEX = re.compile(r"\b(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)\s+de\s+(\d{4})\b", re.IGNORECASE)


def parse_publication_date(text: str) -> datetime | None:
    """
    Extrai a data de publicacao do texto de um bloco de edital.

    Espera datas no formato usado pela FACEPE, como "28 de maio de 2026".
    Retorna None quando nao encontra uma data valida.
    """
    match = DATE_REGEX.search(text or "")
    if not match:
        return None

    day = int(match.group(1))
    month = MONTHS.get(normalize_text(match.group(2)))
    year = int(match.group(3))
    if not month:
        return None

    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def extract_title(item) -> str:
    """
    Extrai o titulo exibido no bloco do edital.

    Na pagina da FACEPE, o titulo fica dentro de uma tag h5 em cada div.edital.
    """
    heading = item.find("h5")
    if heading is None:
        return ""
    return heading.get_text(" ", strip=True)


def extract_primary_pdf_url(item) -> str:
    """
    Extrai a URL do PDF principal do bloco de edital.

    Primeiro tenta usar o link do titulo, que normalmente aponta para o documento principal.
    Se nao encontrar, usa o botao de download como fallback.
    """
    heading_link = item.select_one("h5 a[href]")
    if heading_link is not None:
        href = str(heading_link.get("href") or "").split("#", 1)[0].strip()
        if href.lower().endswith(".pdf"):
            return href

    button = item.select_one("a.avia-button[href]")
    if button is None:
        return ""

    href = str(button.get("href") or "").split("#", 1)[0].strip()
    return href if href.lower().endswith(".pdf") else ""


def parse_calls(html: str, target_year: int) -> list[FacepeCall]:
    """
    O parser que extrai e valida a data de publicação, o título e a URL do PDF principal de cada edital da FACEPE.
    Transforma o HTML da FACEPE em editais principais do ano-alvo."""
    soup = BeautifulSoup(html, "lxml")
    calls: list[FacepeCall] = []
    seen: set[str] = set()

    for position, item in enumerate(soup.select("div.edital.clearfix")):
        title = extract_title(item)
        if not is_primary_edital(title):
            continue

        publication_date = parse_publication_date(item.get_text(" ", strip=True))
        if publication_date is None or publication_date.year != target_year:
            continue

        pdf_url = extract_primary_pdf_url(item)
        if not pdf_url or pdf_url in seen:
            continue

        seen.add(pdf_url)
        calls.append(
            FacepeCall(
                title=title,
                pdf_url=pdf_url,
                publication_date=publication_date,
                position=position,
            )
        )

    return calls
