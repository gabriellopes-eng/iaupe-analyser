import re
import unicodedata


def normalize_text(value: str) -> str:
    """Remove acentos, normaliza espacos e converte texto para minusculas."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def clean_href(href: str) -> str:
    """Remove fragmentos e corrige URLs de PDF com barra final indevida."""
    cleaned = (href or "").split("#", 1)[0].strip()
    if cleaned.endswith("/") and cleaned.lower().endswith(".pdf/"):
        cleaned = cleaned[:-1]
    return cleaned
