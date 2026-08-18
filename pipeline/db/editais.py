from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError, PyMongoError

from .collections import coll
from .connection import disable_mongo


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
