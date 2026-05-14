from typing import TypedDict
from urllib.parse import urljoin

import requests

from .client import (
    fetch_document_entries,
    fetch_open_chamadas,
    get_oauth_token,
    get_site_origin,
)
from .constants import BASE_URL


class FinepDocument(TypedDict):
    chamada_titulo: str
    documento_nome: str
    data: str
    pdf_url: str
    chamada_url: str


LAST_COLLECTED_DOCUMENTS: list[FinepDocument] = []


def is_pdf(pdf_url: str, name: str) -> bool:
    lower_url = pdf_url.lower()
    lower_name = name.lower()
    if lower_url.endswith(".csv") or lower_url.endswith(".odt"):
        return False
    return lower_url.endswith(".pdf") or ".pdf?" in lower_url or lower_name.endswith(".pdf")


def extract_document(
    *,
    origin: str,
    chamada_titulo: str,
    chamada_url: str,
    entry: dict,
) -> FinepDocument | None:
    legenda = str(entry.get("legenda") or "").strip()
    data = str(entry.get("dateCreated") or "").strip()

    fallback: FinepDocument | None = None
    for field_name in ("documentoProprietario", "documentoAberto"):
        doc_field = entry.get(field_name) or {}
        href = str((doc_field.get("link") or {}).get("href") or "").strip()
        if not href:
            continue

        nome = str(doc_field.get("name") or "").strip()
        pdf_url = urljoin(origin, href)
        if not is_pdf(pdf_url, nome):
            continue

        doc: FinepDocument = {
            "chamada_titulo": chamada_titulo,
            "documento_nome": legenda or nome or "Documento sem nome",
            "data": data,
            "pdf_url": pdf_url,
            "chamada_url": chamada_url,
        }
        if "edital" in doc["documento_nome"].lower():
            return doc
        if fallback is None:
            fallback = doc

    return fallback


def fetch_primary_pdf_for_chamada(
    *,
    origin: str,
    token: str,
    chamada_id: int,
    chamada_titulo: str,
    chamada_url: str,
) -> FinepDocument | None:
    items = fetch_document_entries(origin, token, chamada_id)
    fallback_doc: FinepDocument | None = None
    vistos: set[str] = set()

    for entry in items:
        doc = extract_document(
            origin=origin,
            chamada_titulo=chamada_titulo,
            chamada_url=chamada_url,
            entry=entry,
        )
        if not doc or doc["pdf_url"] in vistos:
            continue

        vistos.add(doc["pdf_url"])
        if "edital" in doc["documento_nome"].lower():
            return doc
        if fallback_doc is None:
            fallback_doc = doc

    return fallback_doc


def collect_documents(url_lista: str = BASE_URL) -> list[FinepDocument]:
    origin = get_site_origin(url_lista)
    documentos: list[FinepDocument] = []
    vistos_pdf_global: set[str] = set()

    try:
        token = get_oauth_token(origin)
        eventos = fetch_open_chamadas(origin, token)
    except requests.RequestException:
        return []

    for evento in eventos:
        try:
            primary_doc = fetch_primary_pdf_for_chamada(
                origin=origin,
                token=token,
                chamada_id=int(evento["id"]),
                chamada_titulo=str(evento["chamada_titulo"]),
                chamada_url=str(evento["chamada_url"]),
            )
        except requests.RequestException:
            continue

        if not primary_doc or primary_doc["pdf_url"] in vistos_pdf_global:
            continue

        vistos_pdf_global.add(primary_doc["pdf_url"])
        documentos.append(primary_doc)

    return documentos


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    LAST_COLLECTED_DOCUMENTS.clear()
    LAST_COLLECTED_DOCUMENTS.extend(collect_documents(url_lista))
    return [doc["pdf_url"] for doc in LAST_COLLECTED_DOCUMENTS]
