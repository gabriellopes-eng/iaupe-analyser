from typing import Optional

from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .connection import get_client, get_db_name, handle_connection_failure

# Todos os editais (de qualquer fonte) vivem numa unica collection fixa. Cada
# documento se identifica pelo campo `fonte` (facepe/cnpq/finep/capes) - a
# regra de coleta continua separada por fonte no codigo, so o armazenamento
# e compartilhado. Nao le de env var de proposito: a antiga MONGODB_COLLECTION
# ficava com um valor legado (de antes do modelo por fonte existir) que nunca
# era respeitado na pratica - deixar configuravel de novo reintroduziria essa
# armadilha silenciosamente.
EDITAIS_COLLECTION_NAME = "editais"

# Preferencias de notificacao por docente (email + areas_interesse + segmentos).
# Mesma collection que o front (front/src/lib/docentes-repository.ts) grava e
# que o script de carga da planilha (sandbox/import_docentes_interesse.py)
# populou. Aqui ela e so LIDA: a pipeline consulta quem casa com o edital novo
# para decidir quem notificar, e nunca escreve preferencia de ninguem.
DOCENTES_COLLECTION_NAME = "docentes"

editais_cache: Optional[Collection] = None
docentes_cache: Optional[Collection] = None


def coll() -> Collection:
    """
    Retorna a collection unica `editais` do MongoDB (com cache) e garante os
    indices usados pelas consultas (url_pdf unico, data_limit_submissao, fonte).
    """
    global editais_cache

    if editais_cache is not None:
        return editais_cache

    try:
        collection = get_client()[get_db_name()][EDITAIS_COLLECTION_NAME]
        collection.create_index([("url_pdf", ASCENDING)], unique=True)
        collection.create_index([("data_limit_submissao", ASCENDING)])
        collection.create_index([("fonte", ASCENDING)])
        editais_cache = collection

    except PyMongoError as exc:
        editais_cache = None
        raise handle_connection_failure(exc) from exc

    return editais_cache


def docentes_coll() -> Collection:
    """
    Retorna a collection `docentes` (com cache), usada so para leitura pela
    pipeline de notificacao de editais novos.

    Nao cria indice aqui: o indice unico de `email` ja e criado por quem
    ESCREVE nessa collection (sandbox/import_docentes_interesse.py), e a
    pipeline nao deve alterar o schema de uma base que ela so consulta.
    """
    global docentes_cache

    if docentes_cache is not None:
        return docentes_cache

    try:
        docentes_cache = get_client()[get_db_name()][DOCENTES_COLLECTION_NAME]
    except PyMongoError as exc:
        docentes_cache = None
        raise handle_connection_failure(exc) from exc

    return docentes_cache
