import os
import re
from datetime import datetime, timezone

from .constants import ACCESSORY_KEYWORDS
from .text_utils import normalize_text

EDITAL_NUMBER_REGEX = re.compile(r"^\s*\d{1,2}/\d{4}\b")


def resolve_target_year() -> int:
    """
    Define o ano-alvo dos editais da FACEPE.

    Por padrao usa o ano atual em UTC. Se FACEPE_TARGET_YEAR estiver definido no ambiente,
    usa esse valor para permitir testes ou execucoes controladas.
    """
    raw = (os.getenv("FACEPE_TARGET_YEAR") or "").strip()
    if raw.isdigit() and len(raw) == 4:
        return int(raw)
    return datetime.now(timezone.utc).year


def is_primary_edital(title: str) -> bool:
    """
    Decide se o bloco representa um edital principal.

    Aceita titulos numerados, como "17/2026", e remove documentos acessorios
    como resultados, erratas, prorrogacoes, enquadramentos e listas.
    """
    normalized = normalize_text(title)
    if not normalized or title.lstrip().startswith("•"):
        return False
    if not EDITAL_NUMBER_REGEX.search(normalized):
        return False
    if any(keyword in normalized for keyword in ACCESSORY_KEYWORDS):
        return False
    return "edital" in normalized or "lancamento" in normalized or "abertura" in normalized
