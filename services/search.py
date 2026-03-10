"""
services/search.py — SearchService orchestrator.

Composes the provider registry to search across one or all sources.
Inherits BaseService for shared utilities.
"""

import time
from services.base import BaseService
from services.providers import get_provider, get_all_providers


class SearchService(BaseService):
    """Orchestrates paper searches across registered providers."""

    # Delay between sequential API calls when searching "all" sources,
    # to be a polite API consumer.
    _INTER_SOURCE_DELAY = 0.3

    def search(self, query: str, source: str = 'all',
               max_results: int = 10) -> list[dict]:
        """
        Search for papers.

        Parameters
        ----------
        query : str
            Search terms.
        source : str
            Provider name (e.g. 'arxiv') or 'all'.
        max_results : int
            Papers per source.

        Returns
        -------
        list[dict]  — unified paper dicts.
        """
        if source != 'all':
            provider = get_provider(source)
            return provider.search(query, max_results) if provider else []

        # Search all sources with a polite delay between each
        results = []
        for i, provider in enumerate(get_all_providers()):
            if i > 0:
                time.sleep(self._INTER_SOURCE_DELAY)
            results.extend(provider.search(query, max_results))
        return results


# Module-level singleton — routes import this.
search_service = SearchService()
