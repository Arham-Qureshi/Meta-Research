"""
services/providers/arxiv.py — ArXiv search provider.

Inherits BaseAPIProvider.  Parses Atom XML from the ArXiv API.
"""

from bs4 import BeautifulSoup
from services.providers.base import BaseAPIProvider


class ArxivProvider(BaseAPIProvider):
    NAME = 'arxiv'
    DISPLAY_NAME = 'ArXiv'
    BASE_URL = 'http://export.arxiv.org/api/query'

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        params = {
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending',
        }
        resp = self._get(self.BASE_URL, params=params)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, 'lxml-xml')
        return [self._normalize_paper(e) for e in soup.find_all('entry')]

    def _normalize_paper(self, entry) -> dict:
        arxiv_id_raw = entry.find('id').text.strip()
        arxiv_id = arxiv_id_raw.split('/abs/')[-1] if '/abs/' in arxiv_id_raw else arxiv_id_raw

        title = entry.find('title').text.strip().replace('\n', ' ')
        summary = entry.find('summary').text.strip().replace('\n', ' ')
        authors = [a.find('name').text.strip() for a in entry.find_all('author')]

        published_tag = entry.find('published')
        published_date = published_tag.text.strip()[:10] if published_tag else ''

        link_tag = entry.find('link', {'rel': 'alternate'})
        abstract_url = link_tag['href'] if link_tag else arxiv_id_raw

        categories = [cat.get('term', '') for cat in entry.find_all('category')]

        return {
            'id': arxiv_id,
            'title': title,
            'authors': ', '.join(authors),
            'summary': self._truncate_summary(summary),
            'full_summary': summary,
            'published': published_date,
            'abstract_url': abstract_url,
            'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}',
            'categories': categories,
            'source': self.NAME,
            'source_name': self.DISPLAY_NAME,
            'citations': 0,
        }
