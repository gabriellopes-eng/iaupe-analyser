from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FacepeCall:
    """Representa um edital principal da FACEPE ja normalizado para ordenacao."""

    title: str
    pdf_url: str
    publication_date: datetime
    position: int
