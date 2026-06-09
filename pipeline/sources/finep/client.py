from base64 import b64encode
from urllib.parse import urljoin, urlparse

import requests

from .constants import (
    BASE_URL,
    CHAMADA_DETAIL_PATH_TEMPLATE,
    CHAMADAS_API_PATH,
    DOCUMENTOS_API_PATH_TEMPLATE,
    FIRST_PAGE,
    MAX_CALLS_FIRST_PAGE,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_TOKEN_PATH,
)


def get_site_origin(url: str = BASE_URL) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    parsed_base = urlparse(BASE_URL)
    return f"{parsed_base.scheme}://{parsed_base.netloc}"


def auth_headers(token: str) -> dict[str, str]:
    return {"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {token}"}


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
        raise RuntimeError("Token OAuth da FINEP não retornado")
    return str(token)


def fetch_open_chamadas(origin: str, token: str) -> list[dict[str, str | int]]:
    '''
    Depois o client filtra apenas chamadas abertas:
    Ou seja: a API retorna por publicação mais recente, 
    o código mantém apenas chamadas abertas e limita a primeira página aos itens mais recentes.
    '''
    api_url = f"{urljoin(origin, CHAMADAS_API_PATH)}&page={FIRST_PAGE}"
    response = requests.get(api_url, headers=auth_headers(token), timeout=30)
    response.raise_for_status()

    items = (response.json() or {}).get("items") or []
    eventos: list[dict[str, str | int]] = []
    vistos: set[int] = set()

    for chamada in items:
        situacao = chamada.get("situacao") or {}
        key = str(situacao.get("key") or "").strip().lower()
        name = str(situacao.get("name") or "").strip().lower()
        if key != "aberta" and name != "aberta":
            continue

        chamada_id = chamada.get("id")
        if not isinstance(chamada_id, int) or chamada_id in vistos:
            continue
        vistos.add(chamada_id)

        eventos.append(
            {
                "id": chamada_id,
                "chamada_titulo": str(chamada.get("titulo") or "Chamada sem título"),
                "chamada_url": urljoin(
                    origin,
                    CHAMADA_DETAIL_PATH_TEMPLATE.format(chamada_id=chamada_id),
                ),
            }
        )
        if len(eventos) >= MAX_CALLS_FIRST_PAGE:
            break

    return eventos


def fetch_document_entries(origin: str, token: str, chamada_id: int) -> list[dict]:
    api_url = (
        f"{urljoin(origin, DOCUMENTOS_API_PATH_TEMPLATE.format(chamada_id=chamada_id))}"
        f"&page={FIRST_PAGE}"
    )
    response = requests.get(api_url, headers=auth_headers(token), timeout=30)
    response.raise_for_status()
    return (response.json() or {}).get("items") or []
