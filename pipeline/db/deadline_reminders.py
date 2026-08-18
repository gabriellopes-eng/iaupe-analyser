from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import PyMongoError

from .collections import coll


def find_deadline_candidates(
    *,
    fonte: Optional[str],
    start_at: datetime,
    end_at: datetime,
) -> list[dict]:
    """
    Busca editais com status ok e data_limit_submissao na janela informada.

    Sem `fonte`, busca em todas as fontes de uma vez (a collection e unica).
    """
    query: dict = {
        "status": "ok",
        "data_limit_submissao": {"$gte": start_at, "$lte": end_at},
    }
    if fonte:
        query["fonte"] = fonte

    try:
        cursor = coll().find(
            query,
            {
                "_id": 0,
                "url_pdf": 1,
                "fonte": 1,
                "resultado": 1,
                "data_limit_submissao": 1,
                "deadline_reminder": 1,
                "interessados": 1,
            },
        )
        return list(cursor)
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao buscar candidatos de lembrete: {exc}")
        return []


def mark_deadline_step_sent(
    *,
    url_pdf: str,
    step_days: int,
    sent_at: Optional[datetime] = None,
) -> bool:
    """
    Marca um marco de lembrete como enviado para evitar reenvio.
    """
    when = sent_at or datetime.now(timezone.utc)
    try:
        result = coll().update_one(
            {
                "url_pdf": url_pdf,
                "deadline_reminder.sent_steps": {"$ne": step_days},
            },
            {
                "$addToSet": {"deadline_reminder.sent_steps": step_days},
                "$set": {
                    "deadline_reminder.last_sent_at": when,
                    "updated_at": when,
                },
            },
        )
        return result.modified_count > 0
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao marcar lembrete enviado: {exc}")
        return False
