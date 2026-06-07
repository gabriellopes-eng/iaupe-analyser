import re
import unicodedata


def normalize_text(value: str) -> str:
    """
    Normaliza texto para comparacoes mais seguras.

    Remove acentos, converte para minusculas e troca espacos repetidos por um espaco unico.
    Isso permite comparar "Prorrogação" como "prorrogacao", por exemplo.
    """
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()
