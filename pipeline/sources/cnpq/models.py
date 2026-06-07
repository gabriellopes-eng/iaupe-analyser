from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CnpqCall:
    """Representa uma chamada aberta do CNPq normalizada para ordenacao."""

    detail_url: str
    position: int
    inscription_start_date: datetime | None = None
