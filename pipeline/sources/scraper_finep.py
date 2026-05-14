from base64 import b64encode
from typing import TypedDict
from urllib.parse import urljoin, urlparse

import requests

SOURCE_KEY = "finep"
SOURCE_LABEL = "FINEP"
BASE_URL = "https://www.finep.gov.br/oportunidades"
MONGO_COLLECTION = "editais_finep"

OAUTH_TOKEN_PATH = "/o/oauth2/token"
CHAMADAS_API_PATH = "/o/c/chamadapublicas?sort=dataDePublicacao:desc"
DOCUMENTOS_API_PATH_TEMPLATE = "/o/c/chamadapublicas/{chamada_id}/documentos?sort=dataDePublicacao:desc"
CHAMADA_DETAIL_PATH_TEMPLATE = "/e/chamada-publica/222684/{chamada_id}"
FIRST_PAGE = 1
MAX_CALLS_FIRST_PAGE = 8

# essas sao as credenciais observadas no frontend da pagina de oportunidades.
OAUTH_CLIENT_ID = "idClientPRD"
OAUTH_CLIENT_SECRET = "secretClientPRD"


class FinepDocument(TypedDict):
    chamada_titulo: str
    documento_nome: str
    data: str
    pdf_url: str
    chamada_url: str


class FinepOpenCall(TypedDict):
    id: int
    chamada_titulo: str
    chamada_url: str


LAST_COLLECTED_DOCUMENTS: list[FinepDocument] = []


def get_site_origin(url: str = BASE_URL) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    parsed_base = urlparse(BASE_URL)
    return f"{parsed_base.scheme}://{parsed_base.netloc}"


def get_oauth_token(origin: str) -> str:
    raw_auth = f"{OAUTH_CLIENT_ID}:{OAUTH_CLIENT_SECRET}".encode("utf-8")
    basic_auth = b64encode(raw_auth).decode("ascii")

    response = requests.post(
        urljoin(origin, OAUTH_TOKEN_PATH),
        data={"grant_type": "client_credentials"},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}",
        },
        timeout=30,
    )
    response.raise_for_status()

    token = (response.json() or {}).get("access_token")
    if not token:
        raise RuntimeError("Token OAuth da FINEP nao retornado")

    return str(token)


def is_open_situacao(chamada: dict) -> bool:
    situacao = chamada.get("situacao") or {}
    situacao_key = str(situacao.get("key") or "").strip().lower()
    situacao_name = str(situacao.get("name") or "").strip().lower()
    return situacao_key == "aberta" or situacao_name == "aberta"


def fetch_open_chamadas(origin: str, token: str) -> list[FinepOpenCall]:
    eventos: list[FinepOpenCall] = []
    vistos: set[int] = set()

    api_url = f"{urljoin(origin, CHAMADAS_API_PATH)}&page={FIRST_PAGE}"
    response = requests.get(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json() or {}
    items = payload.get("items") or []

    for chamada in items:
        if not is_open_situacao(chamada):
            continue

        chamada_id = chamada.get("id")
        if not isinstance(chamada_id, int):
            continue

        if chamada_id in vistos:
            continue
        vistos.add(chamada_id)

        eventos.append(
            {
                "id": chamada_id,
                "chamada_titulo": str(chamada.get("titulo") or "Chamada sem titulo"),
                "chamada_url": urljoin(
                    origin,
                    CHAMADA_DETAIL_PATH_TEMPLATE.format(chamada_id=chamada_id),
                ),
            }
        )

        if len(eventos) >= MAX_CALLS_FIRST_PAGE:
            break
    return eventos


def build_documents_from_entry(
    origin: str,
    chamada_titulo: str,
    chamada_url: str,
    entry: dict,
) -> list[FinepDocument]:
    docs: list[FinepDocument] = []
    legenda = str(entry.get("legenda") or "").strip()
    data = str(entry.get("dateCreated") or "").strip()

    for field_name in ("documentoProprietario", "documentoAberto"):
        doc_field = entry.get(field_name) or {}
        href = str((doc_field.get("link") or {}).get("href") or "").strip()
        if not href:
            continue

        name = str(doc_field.get("name") or "").strip()
        pdf_url = urljoin(origin, href)
        lower = pdf_url.lower()
        if lower.endswith(".csv") or lower.endswith(".odt"):
            continue
        if not (lower.endswith(".pdf") or ".pdf?" in lower or name.lower().endswith(".pdf")):
            continue

        docs.append(
            {
                "chamada_titulo": chamada_titulo,
                "documento_nome": legenda or name or "Documento sem nome",
                "data": data,
                "pdf_url": pdf_url,
                "chamada_url": chamada_url,
            }
        )

    return docs


def fetch_pdf_documents_for_chamada(
    *,
    origin: str,
    token: str,
    chamada_id: int,
    chamada_titulo: str,
    chamada_url: str,
) -> list[FinepDocument]:
    docs: list[FinepDocument] = []
    vistos: set[str] = set()

    api_url = (
        f"{urljoin(origin, DOCUMENTOS_API_PATH_TEMPLATE.format(chamada_id=chamada_id))}"
        f"&page={FIRST_PAGE}"
    )
    response = requests.get(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json() or {}
    items = payload.get("items") or []
    for entry in items:
        for doc in build_documents_from_entry(
            origin=origin,
            chamada_titulo=chamada_titulo,
            chamada_url=chamada_url,
            entry=entry,
        ):
            if doc["pdf_url"] in vistos:
                continue
            vistos.add(doc["pdf_url"])
            docs.append(doc)

    return docs


def pick_main_document(docs: list[FinepDocument]) -> FinepDocument | None:
    if not docs:
        return None

    for doc in docs:
        if "edital" in (doc.get("documento_nome") or "").lower():
            return doc

    return docs[0]


def collect_documents(url_lista: str = BASE_URL) -> list[FinepDocument]:
    documentos: list[FinepDocument] = []
    vistos_pdf_global: set[str] = set()

    origin = get_site_origin(url_lista)

    try:
        token = get_oauth_token(origin)
        eventos = fetch_open_chamadas(origin, token)
    except Exception as exc:
        print(f"[FINEP] Falha ao consultar chamadas abertas: {exc}")
        return []

    if not eventos:
        return []

    for evento in eventos:
        chamada_id = evento["id"]
        chamada_titulo = evento["chamada_titulo"]
        url_evento = evento["chamada_url"]

        try:
            docs_evento = fetch_pdf_documents_for_chamada(
                origin=origin,
                token=token,
                chamada_id=chamada_id,
                chamada_titulo=chamada_titulo,
                chamada_url=url_evento,
            )
        except requests.RequestException:
            continue

        doc_principal = pick_main_document(docs_evento)
        if not doc_principal:
            continue

        if doc_principal["pdf_url"] in vistos_pdf_global:
            continue

        vistos_pdf_global.add(doc_principal["pdf_url"])
        documentos.append(doc_principal)

    return documentos


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    global LAST_COLLECTED_DOCUMENTS

    LAST_COLLECTED_DOCUMENTS = collect_documents(url_lista)

    return [doc["pdf_url"] for doc in LAST_COLLECTED_DOCUMENTS]
