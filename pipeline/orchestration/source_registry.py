import os

from sources import cnpq, facepe, finep, scraper_capes

# catalogo central de fontes suportadas pela pipeline
SOURCE_REGISTRY = {
    facepe.SOURCE_KEY: {
        "label": facepe.SOURCE_LABEL,
        "base_url": facepe.BASE_URL,
        "mongo_collection": facepe.MONGO_COLLECTION,
        "collect_links": facepe.collect_links,
    },
    cnpq.SOURCE_KEY: {
        "label": cnpq.SOURCE_LABEL,
        "base_url": cnpq.BASE_URL,
        "mongo_collection": cnpq.MONGO_COLLECTION,
        "collect_links": cnpq.collect_links,
    },
    finep.SOURCE_KEY: {
        "label": finep.SOURCE_LABEL,
        "base_url": finep.BASE_URL,
        "mongo_collection": finep.MONGO_COLLECTION,
        "collect_links": finep.collect_links,
    },
    scraper_capes.SOURCE_KEY: {
        "label": scraper_capes.SOURCE_LABEL,
        "base_url": scraper_capes.BASE_URL,
        "mongo_collection": scraper_capes.MONGO_COLLECTION,
        "collect_links": scraper_capes.collect_links,
    },
}

DEFAULT_SOURCE = (os.getenv("PIPELINE_SOURCE") or "facepe").strip().lower()


def get_source_config(source_key: str | None) -> tuple[str, dict]:
    """
    Resolve a configuracao da fonte selecionada.

    Retorna (source_key_normalizada, configuracao_da_fonte).
    """
    selected_key = (source_key or DEFAULT_SOURCE).strip().lower()
    source = SOURCE_REGISTRY.get(selected_key)
    if source is None:
        disponiveis = ", ".join(sorted(SOURCE_REGISTRY))
        raise ValueError(f"Fonte invalida: {selected_key!r}. Opcoes: {disponiveis}")
    return selected_key, source
