from .client import build_fallback_urls, fetch_html, get_with_retry
from .constants import BASE_URL, SOURCE_KEY, SOURCE_LABEL
from .models import CapesDocument
from .parser import (
    collect_open_call_pages,
    extract_first_pdf_url,
    find_editais_table,
    find_heading,
    parse_documents_from_program_page,
    parse_ptbr_date,
)
from .policy import (
    is_pdf_url,
    is_primary_edital,
    is_target_year_document,
    resolve_target_year,
)
from .scraper import collect_documents, collect_links
from .text_utils import clean_href, normalize_text

__all__ = [
    "SOURCE_KEY",
    "SOURCE_LABEL",
    "BASE_URL",
    "CapesDocument",
    "normalize_text",
    "clean_href",
    "resolve_target_year",
    "is_pdf_url",
    "is_target_year_document",
    "is_primary_edital",
    "build_fallback_urls",
    "get_with_retry",
    "fetch_html",
    "parse_ptbr_date",
    "find_heading",
    "collect_open_call_pages",
    "find_editais_table",
    "extract_first_pdf_url",
    "parse_documents_from_program_page",
    "collect_documents",
    "collect_links",
]
