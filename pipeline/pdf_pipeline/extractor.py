import os
import shutil
from io import BytesIO

import pdfplumber
import requests
from bs4 import BeautifulSoup

try:
    import pypdfium2 as pdfium
    import pytesseract
except ImportError:
    pdfium = None
    pytesseract = None

# No Linux (runner do GitHub Actions), o apt instala o tesseract no PATH e o
# shutil.which ja resolve. No Windows local, o instalador padrao nao entra no
# PATH, entao caimos para o caminho default do instalador quando ele existir.
if pytesseract is not None:
    _tesseract_cmd = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Paginas maximas cobertas pelo OCR quando o PDF nao tem texto selecionavel.
# OCR e bem mais lento que extracao de texto normal, entao limitamos o custo
# em documentos grandes mesmo quando max_pages nao foi informado pelo chamador.
OCR_MAX_PAGES_DEFAULT = 20

# Escala de renderizacao da pagina antes do OCR (1.0 = 72 DPI). 2.0 (~144 DPI)
# equilibra legibilidade do texto com tempo de processamento.
OCR_RENDER_SCALE = 2.0


def ocr_pdf_bytes(content: bytes, max_pages: int | None) -> str:
    """
    Extrai texto via OCR quando o PDF nao tem camada de texto real.

    Isso cobre tanto scans/fotos quanto PDFs onde cada letra foi "impressa"
    como forma vetorial (retangulos/curvas) em vez de caractere de fonte -
    caso comum quando o documento original vem de um visualizador que
    bloqueia copia/selecao de texto. Em ambos os casos, so da pra "ler" a
    pagina renderizando ela como imagem e reconhecendo os caracteres visualmente.
    """
    if pytesseract is None or pdfium is None:
        return ""

    try:
        pdf = pdfium.PdfDocument(BytesIO(content))
        limit = len(pdf) if max_pages is None else min(max_pages, len(pdf))

        texto = ""
        for i in range(limit):
            pagina_bitmap = pdf[i].render(scale=OCR_RENDER_SCALE)
            imagem = pagina_bitmap.to_pil()
            texto += pytesseract.image_to_string(imagem, lang="por") + "\n"

        return texto.strip()
    except Exception as exc:
        print(f"Falha no OCR: {exc}")
        return ""


def looks_like_pdf(url: str, content_type: str, content: bytes) -> bool:
    lower_url = (url or "").lower()
    lower_type = (content_type or "").lower()
    if lower_url.endswith(".pdf"):
        return True
    if "application/pdf" in lower_type:
        return True
    return bool(content and content.startswith(b"%PDF"))


def extract_text_from_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "lxml")

    # remove ruido comum de navegacao para priorizar conteudo principal
    for tag in soup.select("script, style, nav, footer, header"):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # normaliza linhas vazias repetidas
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_text_from_pdf_url(url_pdf: str, max_pages: int | None = None) -> str:
    """
    Baixa um PDF via URL e extrai texto das primeiras páginas.

    Observações:
      - Não salva o PDF em disco: tudo é processado em memória (BytesIO).
      - Extração é feita com pdfplumber (depende do PDF conter texto selecionável;
        PDFs escaneados podem retornar vazio).

    Args:
        url_pdf: URL direta para o PDF.
        max_pages: máximo de páginas para extrair (default: None, ou seja, todas as páginas).

    Returns:
        Texto extraído (string). Retorna "" em caso de falha no download.
    """

    # baixa o recurso remoto para memoria
    try:
        resp = requests.get(url_pdf, headers=REQUEST_HEADERS, timeout=30)
    except requests.RequestException as exc:
        print(f"Erro ao baixar {url_pdf}: {exc}")
        return ""

    if resp.status_code != 200:
        print(f"Erro ao baixar {url_pdf} (status={resp.status_code})")
        return ""

    content_type = resp.headers.get("Content-Type", "")
    content = resp.content

    if not looks_like_pdf(url_pdf, content_type, content):
        # fallback para fontes que fornecem pagina HTML em vez de PDF direto
        html_text = extract_text_from_html(content)
        if not html_text:
            print(f"Recurso nao eh PDF e nao foi possivel extrair texto HTML: {url_pdf}")
        return html_text

    texto = ""

    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            # concatena texto pagina a pagina, respeitando max_pages quando informado
            for i, pagina in enumerate(pdf.pages):
                if max_pages is not None and i >= max_pages:
                    break
                texto += (pagina.extract_text() or "") + "\n"
    except Exception as exc:
        print(f"Falha ao extrair PDF {url_pdf}: {exc}")
        return ""

    texto = texto.strip()
    if texto:
        return texto

    # pdfplumber nao achou nenhum caractere: PDF sem camada de texto real
    # (scan/foto, ou paginas "impressas" como vetor). Tenta OCR como ultimo recurso.
    print(f"Texto vazio via extracao direta, tentando OCR: {url_pdf}")
    return ocr_pdf_bytes(content, max_pages if max_pages is not None else OCR_MAX_PAGES_DEFAULT)
