"""
services/providers/base.py — Abstract Base API Provider.

All search providers inherit BaseAPIProvider to guarantee:
    • A uniform search(query, max_results) → list[dict] interface
    • A uniform _normalize_paper(raw) → dict contract
    • Shared HTTP from BaseService (no duplicate requests code)

Adding a new search source = subclass this, implement search() +
_normalize_paper(), register in __init__.py.  Zero changes elsewhere.
"""

from abc import abstractmethod
from services.base import BaseService


class BaseAPIProvider(BaseService):
    """Abstract base class for paper search API providers."""

    NAME: str = ''             # e.g. 'arxiv'
    DISPLAY_NAME: str = ''     # e.g. 'ArXiv'
    BASE_URL: str = ''         # e.g. 'http://export.arxiv.org/api/query'

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search for papers matching *query*.

        Must return a list of normalised paper dicts (via _normalize_paper).
        """
        raise NotImplementedError

    @abstractmethod
    def _normalize_paper(self, raw: dict) -> dict:
        """
        Convert one API-specific result into the unified paper schema:

        {
            id, title, authors, summary, full_summary,
            published, abstract_url, pdf_url, categories,
            source, source_name, citations, journal?
        }
        """
        raise NotImplementedError

    def _truncate_summary(self, text: str, max_len: int = 500) -> str:
        """Create a short summary field from the full abstract."""
        if not text:
            return ''
        return text[:max_len] + ('...' if len(text) > max_len else '')
