from pymongo.errors import PyMongoError

from .collections import docentes_coll


def list_docentes_com_preferencias() -> list[dict]:
    """
    Lista os docentes que marcaram pelo menos uma area OU um segmento.

    Quem nao marcou nada fica de fora de proposito: preferencia vazia significa
    "ainda nao escolheu", nao "quer tudo". Quem precisa receber todos os editais
    continua sendo atendido pelo e-mail institucional do pipeline_runner
    (RECIPIENT_EMAIL, ver emails/saved_record_email_notifier.py).

    A base tem ordem de centenas de docentes, entao a lista inteira e carregada
    uma vez por execucao e o cruzamento com cada edital acontece em memoria
    (ver orchestration/docente_match.py). Isso evita uma consulta por edital e,
    principalmente, permite comparar os valores NORMALIZADOS - o Mongo compararia
    string crua e perderia os registros da planilha legada.
    """
    query = {
        "$or": [
            {"areas_interesse": {"$exists": True, "$ne": []}},
            {"segmentos": {"$exists": True, "$ne": []}},
        ]
    }

    try:
        cursor = docentes_coll().find(
            query,
            {"_id": 0, "email": 1, "areas_interesse": 1, "segmentos": 1},
        )
        return list(cursor)
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao listar docentes com preferencias: {exc}")
        return []
