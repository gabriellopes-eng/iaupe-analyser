import os
from datetime import datetime, timezone
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv(override=True)

# Todos os editais (de qualquer fonte) vivem numa unica collection fixa. Cada
# documento se identifica pelo campo `fonte` (facepe/cnpq/finep/capes) - a
# regra de coleta continua separada por fonte no codigo, so o armazenamento
# e compartilhado. Nao le de env var de proposito: a antiga MONGODB_COLLECTION
# ficava com um valor legado (de antes do modelo por fonte existir) que nunca
# era respeitado na pratica - deixar configuravel de novo reintroduziria essa
# armadilha silenciosamente.
EDITAIS_COLLECTION_NAME = "editais"

client_cache: Optional[MongoClient] = None
collection_cache: Optional[Collection] = None
mongo_disabled = False
mongo_disable_reason: Optional[str] = None


def disable_mongo(reason: str) -> None:
    """Desabilita persistencia no Mongo apos falha critica de conexao."""
    global mongo_disabled, mongo_disable_reason

    if mongo_disabled:
        return

    mongo_disabled = True
    mongo_disable_reason = reason
    print(f"[MongoDB] Persistencia desabilitada: {reason}")


def mongo_is_requested() -> bool:
    """Define se o Mongo deve ser usado com base em env vars."""
    raw_value = (os.getenv("MONGODB_ENABLED") or "auto").strip().lower()
    if raw_value in {"0", "false", "no", "off", "disabled"}:
        return False

    uri = (os.getenv("MONGODB_URI") or "").strip()
    return bool(uri)


def coll() -> Collection:
    """
    Retorna a collection unica `editais` do MongoDB (com cache) e garante os
    indices usados pelas consultas (url_pdf unico, data_limit_submissao, fonte).
    """
    global client_cache, collection_cache

    if collection_cache is not None:
        return collection_cache

    if mongo_disabled or not mongo_is_requested():
        raise RuntimeError(mongo_disable_reason or "MongoDB desabilitado ou nao configurado")

    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()
    server_selection_timeout_ms = int(
        (os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS") or "30000").strip()
    )
    connect_timeout_ms = int(
        (os.getenv("MONGODB_CONNECT_TIMEOUT_MS") or "30000").strip()
    )
    socket_timeout_ms = int(
        (os.getenv("MONGODB_SOCKET_TIMEOUT_MS") or "30000").strip()
    )

    try:
        #É aí que o driver abre conexão TLS com Atlas.
        # cria cliente apenas uma vez e reaproveita nas chamadas seguintes
        if client_cache is None:
            client_cache = MongoClient(
                uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                retryWrites=True,
            )

        collection = client_cache[db_name][EDITAIS_COLLECTION_NAME]
        collection.create_index([("url_pdf", ASCENDING)], unique=True)
        collection.create_index([("data_limit_submissao", ASCENDING)])
        collection.create_index([("fonte", ASCENDING)])
        collection_cache = collection

    except PyMongoError as exc:
        client_cache = None
        collection_cache = None
        disable_mongo(str(exc))
        raise RuntimeError(mongo_disable_reason or "Falha ao conectar no MongoDB") from exc

    return collection_cache

# Essa funcao serve para verificar se um edital ja foi processado com status "ok"
# antes de tentar analisar e salvar novamente, o que economiza recursos de IA
# e evita atualizacoes desnecessarias no MongoDB. Ela é chamada no pipeline_runner antes de processar cada link, e se retornar True, o pipeline simplesmente pula para o proximo link sem gastar recursos com analise ou persistencia.
def already_exists(url_pdf: str) -> bool:
    """Verifica se um edital ja foi salvo com status ok."""
    try:
        doc = coll().find_one({"url_pdf": url_pdf}, {"_id": 1, "status": 1})
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao consultar already_exists: {exc}")
        return False

    return bool(doc) and doc.get("status") == "ok"


def save(
    url_pdf: str,
    resultado: dict,
    fonte: str,
    texto_preview: Optional[str] = None,
    data_limit_submissao: Optional[datetime] = None,
) -> str:
    """
    Persiste (insert/update) o resultado da analise de um edital.

    Retorna: inserted | updated | disabled
    """
    now = datetime.now(timezone.utc)

    doc_set = {
        "url_pdf": url_pdf,
        "fonte": fonte,
        "resultado": resultado,
        "status": "ok" if "erro" not in (resultado or {}) else "erro",
        "data_limit_submissao": data_limit_submissao,
        "updated_at": now,
    }

    if texto_preview is not None:
        doc_set["texto_preview"] = texto_preview[:2000]

    try:
        # insert preferencial para manter created_at apenas na primeira gravacao
        collection = coll()
        collection.insert_one({**doc_set, "created_at": now})
        return "inserted"

    except DuplicateKeyError:
        # se ja existe url_pdf, atualiza campos mutaveis
        try:
            collection = coll()
            collection.update_one({"url_pdf": url_pdf}, {"$set": doc_set})
            return "updated"
        except (RuntimeError, PyMongoError) as exc:
            print(f"[MongoDB] Falha ao atualizar documento duplicado: {exc}")
            return "disabled"

    except RuntimeError:
        return "disabled"

    except PyMongoError as exc:
        disable_mongo(str(exc))
        return "disabled"


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
