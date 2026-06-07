from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CapesDocument:
    """Representa um edital principal da CAPES normalizado para ordenacao."""

    title: str
    pdf_url: str
    publication_date: datetime
    source_page_url: str
    position: int
