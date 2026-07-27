import os
import re
from datetime import datetime, timezone

from .constants import ACCESSORY_KEYWORDS
from .text_utils import normalize_text

EDITAL_YEAR_REGEX_TEMPLATE = r"\bedital\b.*\b{year}\b"


def resolve_target_year() -> int:
    """
    Define o ano-alvo dos editais da CAPES.

    Por padrao usa o ano atual em UTC. Se CAPES_TARGET_YEAR estiver definido no ambiente,
    usa esse valor para permitir testes ou execucoes controladas.
    """
    raw = (os.getenv("CAPES_TARGET_YEAR") or "").strip()
    if raw.isdigit() and len(raw) == 4:
        return int(raw)
    return datetime.now(timezone.utc).year


def is_pdf_url(url: str) -> bool:
    """Identifica URLs que apontam para PDF.

    O gov.br passou a servir arquivos com sufixo apos a extensao
    (".pdf/@@display-file/file", ".pdf/@@download/file"), entao nao basta
    checar o final da URL - o ".pdf" pode vir seguido de "/" ou "?".
    """
    lower_url = (url or "").lower()
    return bool(re.search(r"\.pdf(?:$|[/?])", lower_url))


def is_target_year_document(title: str, url: str, target_year: int) -> bool:
    """Confere se titulo ou URL indicam o ano-alvo da execucao."""
    year = str(target_year)
    return year in normalize_text(f"{title} {url}")


def is_primary_edital(title: str, target_year: int) -> bool:
    """
    Decide se uma linha da tabela representa edital principal.

    Remove alteracoes, anexos, termos, modelos, portarias e outros documentos
    auxiliares que aparecem na mesma tabela dos editais.
    """
    normalized = normalize_text(title)
    if "edital" not in normalized:
        return False
    if any(keyword in normalized for keyword in ACCESSORY_KEYWORDS):
        return False

    edital_year_regex = EDITAL_YEAR_REGEX_TEMPLATE.format(year=target_year)
    return bool(re.search(edital_year_regex, normalized))
