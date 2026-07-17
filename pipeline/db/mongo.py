import os
from datetime import datetime, timezone
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv(override=True)

client_cache: Optional[MongoClient] = None
collection_cache: dict[str, Collection] = {}
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


def resolve_collection_name(collection_name: Optional[str]) -> str:
    """Resolve nome da collection com fallback para configuracao global."""
    resolved = (collection_name or os.getenv("MONGODB_COLLECTION") or "editais").strip()
    return resolved or "editais"


def coll(collection_name: Optional[str] = None, ensure_edital_indexes: bool = True) -> Collection:
    """
    Retorna a collection do MongoDB (com cache).

    Quando ensure_edital_indexes=True (padrao), garante os indices usados pelas
    collections de editais (url_pdf unico, data_limit_submissao). Passe False
    para collections de outro formato, como preferencias do usuario.
    """
    global client_cache, collection_cache

    coll_name = resolve_collection_name(collection_name)

    if coll_name in collection_cache:
        return collection_cache[coll_name]

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

        # cache da collection por nome para reduzir overhead
        collection = client_cache[db_name][coll_name]
        if ensure_edital_indexes:
            collection.create_index([("url_pdf", ASCENDING)], unique=True)
            collection.create_index([("data_limit_submissao", ASCENDING)])
        collection_cache[coll_name] = collection

    except PyMongoError as exc:
        client_cache = None
        collection_cache = {}
        disable_mongo(str(exc))
        raise RuntimeError(mongo_disable_reason or "Falha ao conectar no MongoDB") from exc

    return collection_cache[coll_name]

# Essa funcao serve para verificar se um edital ja foi processado com status "ok" 
# antes de tentar analisar e salvar novamente, o que economiza recursos de IA 
# e evita atualizacoes desnecessarias no MongoDB. Ela é chamada no pipeline_runner antes de processar cada link, e se retornar True, o pipeline simplesmente pula para o proximo link sem gastar recursos com analise ou persistencia.
def already_exists(url_pdf: str, collection_name: Optional[str] = None) -> bool:
    """Verifica se um edital ja foi salvo com status ok."""
    try:
        doc = coll(collection_name).find_one({"url_pdf": url_pdf}, {"_id": 1, "status": 1})
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao consultar already_exists: {exc}")
        return False

    return bool(doc) and doc.get("status") == "ok"


def save(
    url_pdf: str,
    resultado: dict,
    texto_preview: Optional[str] = None,
    collection_name: Optional[str] = None,
    data_limit_submissao: Optional[datetime] = None,
) -> str:
    """
    Persiste (insert/update) o resultado da analise de um edital.

    Retorna: inserted | updated | disabled
    """
    now = datetime.now(timezone.utc)

    doc_set = {
        "url_pdf": url_pdf,
        "resultado": resultado,
        "status": "ok" if "erro" not in (resultado or {}) else "erro",
        "data_limit_submissao": data_limit_submissao,
        "updated_at": now,
    }

    if texto_preview is not None:
        doc_set["texto_preview"] = texto_preview[:2000]

    try:
        # insert preferencial para manter created_at apenas na primeira gravacao
        collection = coll(collection_name)
        collection.insert_one({**doc_set, "created_at": now})
        return "inserted"

    except DuplicateKeyError:
        # se ja existe url_pdf, atualiza campos mutaveis
        try:
            collection = coll(collection_name)
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


PREFERENCES_COLLECTION = "preferencias_usuario"
PREFERENCES_DOC_ID = "fontes_seguidas"


def get_followed_sources() -> set[str]:
    """
    Le as fontes que o usuario segue (preferencia global, sem multi-usuario ainda).

    Mesmo documento/collection que o front-end Next.js le e escreve.
    """
    try:
        doc = coll(PREFERENCES_COLLECTION, ensure_edital_indexes=False).find_one(
            {"_id": PREFERENCES_DOC_ID}
        )
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao ler preferencias de fontes: {exc}")
        return set()

    if not doc:
        return set()

    fontes = doc.get("fontes_seguidas") or []
    return {str(f).strip().lower() for f in fontes if str(f).strip()}


def set_source_followed(source_key: str, followed: bool) -> str:
    """
    Liga ou desliga uma fonte na lista de fontes seguidas pelo usuario.

    Retorna: updated | disabled
    """
    op = "$addToSet" if followed else "$pull"
    try:
        coll(PREFERENCES_COLLECTION, ensure_edital_indexes=False).update_one(
            {"_id": PREFERENCES_DOC_ID},
            {
                op: {"fontes_seguidas": source_key},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
        return "updated"
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao atualizar preferencias de fontes: {exc}")
        return "disabled"


def find_deadline_candidates(
    *,
    collection_name: Optional[str],
    start_at: datetime,
    end_at: datetime,
) -> list[dict]:
    """Busca editais com status ok e data_limit_submissao na janela informada."""
    query = {
        "status": "ok",
        "data_limit_submissao": {"$gte": start_at, "$lte": end_at},
    }

    try:
        cursor = coll(collection_name).find(
            query,
            {
                "_id": 0,
                "url_pdf": 1,
                "resultado": 1,
                "data_limit_submissao": 1,
                "deadline_reminder": 1,
            },
        )
        return list(cursor)
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao buscar candidatos de lembrete: {exc}")
        return []


def mark_deadline_step_sent(
    *,
    collection_name: Optional[str],
    url_pdf: str,
    step_days: int,
    sent_at: Optional[datetime] = None,
) -> bool:
    """
    Marca um marco de lembrete como enviado para evitar reenvio.
    """
    when = sent_at or datetime.now(timezone.utc)
    try:
        result = coll(collection_name).update_one(
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
