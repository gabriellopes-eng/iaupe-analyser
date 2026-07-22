"""
Script de migracao one-shot: copia os documentos das 4 collections antigas
(editais_facepe, editais_cnpq, editais_finep, editais_capes) para uma
collection unica `editais`, adicionando o campo `fonte` em cada documento.

As collections antigas NAO sao apagadas por este script - ficam de backup ate
confirmar que tudo funciona na nova. Seguro rodar mais de uma vez: documentos
ja migrados (mesma url_pdf) sao pulados por causa do indice unico.

Uso (dentro da pasta pipeline/):
    python scripts/migrate_to_single_collection.py
"""

from __future__ import annotations

import os

import certifi
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

load_dotenv(override=True)

OLD_COLLECTIONS = {
    "facepe": "editais_facepe",
    "cnpq": "editais_cnpq",
    "finep": "editais_finep",
    "capes": "editais_capes",
}
NEW_COLLECTION = "editais"


def main() -> None:
    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        print("MONGODB_URI nao configurado no .env.")
        return

    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()
    client = MongoClient(uri, tlsCAFile=certifi.where())
    db = client[db_name]

    new_coll = db[NEW_COLLECTION]
    new_coll.create_index([("url_pdf", ASCENDING)], unique=True)
    new_coll.create_index([("data_limit_submissao", ASCENDING)])
    new_coll.create_index([("fonte", ASCENDING)])

    total_migrated = 0
    total_skipped = 0

    for fonte, old_name in OLD_COLLECTIONS.items():
        old_coll = db[old_name]
        docs = list(old_coll.find({}))
        print(f"{old_name}: {len(docs)} documento(s) encontrados.")

        for doc in docs:
            doc = dict(doc)
            doc.pop("_id", None)
            doc["fonte"] = fonte

            try:
                new_coll.insert_one(doc)
                total_migrated += 1
            except DuplicateKeyError:
                # ja migrado numa execucao anterior (mesma url_pdf) - seguro pular
                total_skipped += 1

    print(f"\nMigracao concluida: {total_migrated} inseridos, {total_skipped} ja existiam.")
    print(f"Total agora em '{NEW_COLLECTION}': {new_coll.count_documents({})}")
    print("\nCollections antigas mantidas como backup (nao foram apagadas).")


if __name__ == "__main__":
    main()
