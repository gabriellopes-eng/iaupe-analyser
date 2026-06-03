import pdfplumber
import requests
from io import BytesIO
from bs4 import BeautifulSoup


REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _looks_like_pdf(url: str, content_type: str, content: bytes) -> bool:
    lower_url = (url or "").lower()
    lower_type = (content_type or "").lower()
    if lower_url.endswith(".pdf"):
        return True
    if "application/pdf" in lower_type:
        return True
    return bool(content and content.startswith(b"%PDF"))


def _extract_text_from_html(content: bytes) -> str:
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

    if not _looks_like_pdf(url_pdf, content_type, content):
        # fallback para fontes que fornecem pagina HTML em vez de PDF direto
        html_text = _extract_text_from_html(content)
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

    return texto.strip()
