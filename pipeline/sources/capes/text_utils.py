import re
import unicodedata


def normalize_text(value: str) -> str:
    """Remove acentos, normaliza espacos e converte texto para minusculas."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def clean_href(href: str) -> str:
    """
    Normaliza URLs de PDF da CAPES para uma forma canonica.

    - remove o fragmento (`#...`);
    - trunca tudo que vier depois de `.pdf`. O gov.br (Plone) serve o MESMO
      arquivo em duas formas: a URL "limpa" (`...edital.pdf`) e a URL de download
      (`...edital.pdf/@@display-file/file` ou `.../@@download/file`, e ate uma
      barra final solta). As duas apontam para o mesmo PDF, mas cada uma virava
      um edital separado no banco. Deixar so `...edital.pdf` evita a duplicata.
    """
    cleaned = (href or "").split("#", 1)[0].strip()
    return re.sub(r"(?i)(\.pdf)/.*$", r"\1", cleaned)
