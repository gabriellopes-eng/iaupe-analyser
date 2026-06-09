from .client import fetch_html
from .constants import BASE_URL
from .parser import parse_calls
from .policy import resolve_target_year


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """
    Coleta links dos editais principais mais recentes da FACEPE.

    O fluxo baixa a pagina de editais abertos, filtra apenas editais principais
    do ano-alvo, ordena por data de publicacao decrescente e retorna as URLs dos PDFs
    
    Aqui a FACEPE baixa a página, transforma os blocos em objetos com publication_date, 
    filtra pelo ano-alvo e ordena por data de publicação decrescente.
    """
    html = fetch_html(url_lista)
    calls = parse_calls(html, target_year=resolve_target_year())
    calls.sort(key=lambda call: (call.publication_date, -call.position), reverse=True)
    return [call.pdf_url for call in calls]
