from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import PyMongoError

from .collections import coll

# Campo gravado no proprio documento do edital com os e-mails ja avisados sobre
# ELE. Mesma ideia do `deadline_reminder.sent_steps` (ver db/deadline_reminders.py):
# o controle de "ja mandei" mora junto do edital, entao reprocessar a fonte ou
# rodar o backfill duas vezes nao gera e-mail repetido para ninguem.
MATCH_NOTIFICATION_FIELD = "match_notification"


def get_match_sent_emails(doc: dict) -> set[str]:
    """Le os e-mails ja notificados de um documento de edital ja carregado."""
    info = doc.get(MATCH_NOTIFICATION_FIELD) or {}
    return {
        str(email).strip().lower()
        for email in (info.get("sent_emails") or [])
        if str(email).strip()
    }


def find_match_notification_candidates(
    *,
    fonte: Optional[str],
    now: Optional[datetime] = None,
) -> list[dict]:
    """
    Busca editais validos para notificar docentes por area/segmento.

    Criterio: analise ok E prazo de submissao identificado E ainda no futuro.

    O prazo e obrigatorio de proposito. A base tem muitos documentos acessorios
    (errata, resultado, lista de espera, enquadramento) que foram analisados e
    ganharam areas/segmentos, mas nao tem `data_limit_submissao`. Sem esse
    filtro, o backfill mandaria e-mail para os docentes sobre "Resultado
    Preliminar" e "ERRATA" - ruido que ninguem pediu. Um edital que vale a pena
    avisar tem prazo para submeter proposta; sem prazo, e outra coisa.

    Sem `fonte`, varre todas as fontes de uma vez (a collection e unica).

    Usado pelo backfill (`main.py --notify-editais`). No fluxo normal a pipeline
    ja notifica logo apos salvar o edital, sem passar por aqui.
    """
    reference = now or datetime.now(timezone.utc)

    query: dict = {
        "status": "ok",
        "data_limit_submissao": {"$gt": reference},
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
                MATCH_NOTIFICATION_FIELD: 1,
            },
        )
        return list(cursor)
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao buscar candidatos de notificacao por area: {exc}")
        return []


def mark_match_emails_sent(
    *,
    url_pdf: str,
    emails: list[str],
    sent_at: Optional[datetime] = None,
) -> int:
    """
    Marca VARIOS destinatarios como avisados sobre este edital, numa unica
    operacao.

    Usado pelo envio em copia oculta: um bloco de BCC entrega para dezenas de
    docentes de uma vez, entao a marcacao tambem e feita em lote logo depois.
    `$addToSet` com `$each` e idempotente - rodar de novo nao duplica nada.

    Devolve quantos e-mails (distintos, normalizados) foram enviados na operacao.
    """
    normalized = sorted({e.strip().lower() for e in (emails or []) if e and e.strip()})
    if not normalized:
        return 0

    when = sent_at or datetime.now(timezone.utc)
    try:
        coll().update_one(
            {"url_pdf": url_pdf},
            {
                "$addToSet": {
                    f"{MATCH_NOTIFICATION_FIELD}.sent_emails": {"$each": normalized}
                },
                "$set": {
                    f"{MATCH_NOTIFICATION_FIELD}.last_sent_at": when,
                    "updated_at": when,
                },
            },
        )
        return len(normalized)
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao marcar notificacoes por area (lote): {exc}")
        return 0


def mark_match_email_sent(
    *,
    url_pdf: str,
    email: str,
    sent_at: Optional[datetime] = None,
) -> bool:
    """
    Marca UM destinatario como ja avisado sobre este edital.

    A marcacao e feita e-mail a e-mail, logo apos cada envio, e nao em lote no
    fim: se a execucao morrer no meio de uma lista grande, quem ja recebeu nao
    recebe de novo na proxima rodada.
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        return False

    when = sent_at or datetime.now(timezone.utc)
    try:
        result = coll().update_one(
            {"url_pdf": url_pdf},
            {
                "$addToSet": {f"{MATCH_NOTIFICATION_FIELD}.sent_emails": normalized},
                "$set": {
                    f"{MATCH_NOTIFICATION_FIELD}.last_sent_at": when,
                    "updated_at": when,
                },
            },
        )
        return result.matched_count > 0
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao marcar notificacao por area enviada: {exc}")
        return False
