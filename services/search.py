import time
from services.base import BaseService
from services.providers import get_provider, get_all_providers

class SearchService(BaseService):

    _INTER_SOURCE_DELAY = 0.3

    def search(self, query: str, source: str = 'all',
               max_results: int = 10) -> list[dict]:

        if source != 'all':
            provider = get_provider(source)
            return provider.search(query, max_results) if provider else []

        results = []
        for i, provider in enumerate(get_all_providers()):
            if i > 0:
                time.sleep(self._INTER_SOURCE_DELAY)
            results.extend(provider.search(query, max_results))
        return results

search_service = SearchService()
