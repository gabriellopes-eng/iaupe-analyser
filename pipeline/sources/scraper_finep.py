import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import TypedDict

SOURCE_KEY = "finep"
SOURCE_LABEL = "FINEP"
BASE_URL = "https://www.finep.gov.br/oportunidades"
MONGO_COLLECTION = "editais_finep"


class FinepDocument(TypedDict):
    chamada_titulo: str
    documento_nome: str
    data: str
    pdf_url: str
    chamada_url: str


# Mantem os metadados da ultima coleta para inspecao/depuracao sem quebrar
# o contrato atual do pipeline (collect_links -> list[str]).
LAST_COLLECTED_DOCUMENTS: list[FinepDocument] = []


def safe_text(node) -> str:
    if not node:
        return ""
    return node.get_text(" ", strip=True)


def request_html(url: str) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def extract_chamada_links(url_lista: str, soup: BeautifulSoup) -> list[str]:
    eventos: list[str] = []
    vistos_eventos: set[str] = set()

    # site com nova estrutura principal.
    selectors = [
        "div.lista-container div.lista-cards div.card.mb-3.chamada-card div.link-interna a[href]",
        "div.lista-cards div.card.mb-3.chamada-card a[href]",
        "div.card.mb-3.chamada-card a[href]",
    ]

    for selector in selectors:
        for a in soup.select(selector):
            href_evento = (a.get("href") or "").split("#", 1)[0].strip()
            if not href_evento:
                continue

            url_evento = urljoin(url_lista, href_evento)

            # Mantem filtro para paginas de chamadas publicas e protege contra
            # pequenas mudancas de rota.
            lower = url_evento.lower()
            if "/chamadas-publicas/" not in lower and "chamadapublica" not in lower:
                continue

            if url_evento not in vistos_eventos:
                vistos_eventos.add(url_evento)
                eventos.append(url_evento)

        if eventos:
            break

    return eventos


def extract_pdf_documents_from_chamada(url_evento: str, soup_evento: BeautifulSoup) -> list[FinepDocument]:
    documentos: list[FinepDocument] = []
    vistos_pdf: set[str] = set()

    # Nova estrutura da secao "Lista de Documentos".
    rows = soup_evento.select(
        "div#documentos-chamada-wrapper table.documentos-table tbody#documentos-body.documentos-list tr"
    )
    if not rows:
        # Fallback mais resiliente para pequenas mudancas de classe/id.
        rows = soup_evento.select("div#documentos-chamada-wrapper tbody tr")

    if not rows:
        return documentos

    titulo_node = soup_evento.select_one("h1") or soup_evento.select_one("h2")
    chamada_titulo = safe_text(titulo_node) or "Chamada sem titulo"

    for row in rows:
        cells = row.select("td")
        data = safe_text(cells[0]) if len(cells) >= 1 else ""
        documento_nome = safe_text(cells[1]) if len(cells) >= 2 else ""
        downloads_cell = row.select_one("td.downloads")
        if not downloads_cell:
            continue

        for a in downloads_cell.select("a[href]"):
            href_doc = (a.get("href") or "").split("#", 1)[0].strip()
            if not href_doc:
                continue

            # Captura somente o link associado ao icone de PDF.
            has_pdf_icon = bool(a.select_one("svg.lexicon-icon-doc-file-pdf"))
            url_doc = urljoin(url_evento, href_doc)
            is_pdf_url = url_doc.lower().endswith(".pdf") or ".pdf" in url_doc.lower()

            if not has_pdf_icon and not is_pdf_url:
                continue

            # Ignora explicitamente formatos nao desejados.
            lower_doc = url_doc.lower()
            if lower_doc.endswith(".csv") or lower_doc.endswith(".odt"):
                continue

            if url_doc in vistos_pdf:
                continue
            vistos_pdf.add(url_doc)

            documentos.append(
                {
                    "chamada_titulo": chamada_titulo,
                    "documento_nome": documento_nome or "Documento sem nome",
                    "data": data,
                    "pdf_url": url_doc,
                    "chamada_url": url_evento,
                }
            )

    return documentos


def collect_documents(url_lista: str = BASE_URL) -> list[FinepDocument]:
    """
    Coleta documentos PDF das chamadas da FINEP com metadados.

    Fluxo:
    1) acessa pagina principal de oportunidades
    2) percorre cards de chamadas publicas
    3) entra em cada pagina de chamada
    4) extrai somente links PDF da tabela "Lista de Documentos"
    """
    try:
        html = request_html(url_lista)
    except requests.RequestException:
        return []

    soup = BeautifulSoup(html, "lxml")
    eventos = extract_chamada_links(url_lista, soup)
    if not eventos:
        return []

    documentos: list[FinepDocument] = []
    vistos_pdf_global: set[str] = set()

    for url_evento in eventos:
        try:
            html_evento = request_html(url_evento)
        except requests.RequestException:
            continue

        soup_evento = BeautifulSoup(html_evento, "lxml")
        docs_evento = extract_pdf_documents_from_chamada(url_evento, soup_evento)
        if not docs_evento:
            # Nao falha a coleta inteira se uma chamada estiver sem PDF.
            continue

        for doc in docs_evento:
            if doc["pdf_url"] in vistos_pdf_global:
                continue
            vistos_pdf_global.add(doc["pdf_url"])
            documentos.append(doc)

    return documentos


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """
    Contrato legado da pipeline: retorna somente lista de URLs de PDF.
    """
    global LAST_COLLECTED_DOCUMENTS
    LAST_COLLECTED_DOCUMENTS = collect_documents(url_lista)
    return [doc["pdf_url"] for doc in LAST_COLLECTED_DOCUMENTS]