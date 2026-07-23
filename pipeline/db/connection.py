import os
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

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
