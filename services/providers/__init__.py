"""
services/providers/__init__.py — Provider Registry.

Auto-discovery pattern: register providers once, SearchService
uses the registry.  Adding a new source = add it here + create the file.
"""

from services.providers.arxiv import ArxivProvider
from services.providers.semantic_scholar import SemanticScholarProvider
from services.providers.crossref import CrossrefProvider
from services.providers.openalex import OpenAlexProvider


# ── Registry ─────────────────────────────────────────────────
# Singleton instances — reused across all requests.
PROVIDERS = {
    'arxiv':            ArxivProvider(),
    'semantic_scholar': SemanticScholarProvider(),
    'crossref':         CrossrefProvider(),
    'openalex':         OpenAlexProvider(),
}


def get_provider(name: str):
    """Return a provider instance by name, or None."""
    return PROVIDERS.get(name)


def get_all_providers():
    """Return all registered provider instances."""
    return PROVIDERS.values()


def get_provider_names() -> list[str]:
    """Return all registered provider names."""
    return list(PROVIDERS.keys())
