import os
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv(override=True)

# So a conexao com o cluster mora aqui - QUAIS collections existem e seus
# indices ficam em db/collections.py. Um modulo so cuida de "como falar com o
# Atlas", o outro de "o que a gente guarda la".

client_cache: Optional[MongoClient] = None
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


def get_db_name() -> str:
    return (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()


def get_client() -> MongoClient:
    """
    Cria (uma unica vez) e devolve o cliente Mongo compartilhado.

    Todas as collections (editais, docentes) usam a MESMA conexao TLS com o
    Atlas, em vez de cada uma abrir a sua.
    """
    global client_cache

    if mongo_disabled or not mongo_is_requested():
        raise RuntimeError(mongo_disable_reason or "MongoDB desabilitado ou nao configurado")

    if client_cache is not None:
        return client_cache

    uri = (os.getenv("MONGODB_URI") or "").strip()
    server_selection_timeout_ms = int(
        (os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS") or "30000").strip()
    )
    connect_timeout_ms = int(
        (os.getenv("MONGODB_CONNECT_TIMEOUT_MS") or "30000").strip()
    )
    socket_timeout_ms = int(
        (os.getenv("MONGODB_SOCKET_TIMEOUT_MS") or "30000").strip()
    )

    #É aí que o driver abre conexão TLS com Atlas.
    # cria cliente apenas uma vez e reaproveita nas chamadas seguintes
    client_cache = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=server_selection_timeout_ms,
        connectTimeoutMS=connect_timeout_ms,
        socketTimeoutMS=socket_timeout_ms,
        retryWrites=True,
    )
    return client_cache


def invalidate_client() -> None:
    """Zera o cliente cacheado. Usado por db/collections.py apos falha de conexao."""
    global client_cache
    client_cache = None


def handle_connection_failure(exc: PyMongoError) -> RuntimeError:
    """
    Ponto unico de reacao a uma falha de conexao/indice: zera o cliente cacheado
    e desabilita o Mongo pro resto da execucao (evita ficar tentando reconectar
    a cada consulta).
    """
    invalidate_client()
    disable_mongo(str(exc))
    return RuntimeError(mongo_disable_reason or "Falha ao conectar no MongoDB")
