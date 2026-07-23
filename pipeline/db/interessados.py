from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from .connection import coll


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def add_interessado(url_pdf: str, email: str) -> str:
    """
    Inscreve um e-mail na lista de interessados de um edital especifico.

    Sem autenticacao: a pessoa so precisa informar o proprio e-mail. Cada edital
    guarda sua propria lista (campo `interessados`), independente da fonte.
    Retorna: updated | not_found | disabled
    """
    normalized = normalize_email(email)
    if not normalized:
        return "not_found"
    try:
        result = coll().update_one(
            {"url_pdf": url_pdf},
            {
                "$addToSet": {"interessados": normalized},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao inscrever interessado: {exc}")
        return "disabled"

    return "updated" if result.matched_count > 0 else "not_found"


def remove_interessado(url_pdf: str, email: str) -> str:
    """Remove um e-mail da lista de interessados de um edital especifico."""
    normalized = normalize_email(email)
    if not normalized:
        return "not_found"
    try:
        result = coll().update_one(
            {"url_pdf": url_pdf},
            {
                "$pull": {"interessados": normalized},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao remover interessado: {exc}")
        return "disabled"

    return "updated" if result.matched_count > 0 else "not_found"


def list_interessados(url_pdf: str) -> list[str]:
    """Lista os e-mails inscritos num edital especifico (uso: CLI/depuracao)."""
    try:
        doc = coll().find_one({"url_pdf": url_pdf}, {"_id": 0, "interessados": 1})
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao listar interessados: {exc}")
        return []

    if not doc:
        return []
    return list(doc.get("interessados") or [])
