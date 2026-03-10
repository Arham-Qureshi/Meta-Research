"""
services/providers/semantic_scholar.py — Semantic Scholar search provider.

Inherits BaseAPIProvider.  Uses the Graph API v1.
"""

from services.providers.base import BaseAPIProvider


class SemanticScholarProvider(BaseAPIProvider):
    NAME = 'semantic_scholar'
    DISPLAY_NAME = 'Semantic Scholar'
    BASE_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        params = {
            'query': query,
            'limit': min(max_results, 20),
            'fields': 'title,authors,abstract,year,externalIds,openAccessPdf,url,citationCount',
        }
        resp = self._get(self.BASE_URL, params=params)
        data = self._safe_json(resp)

        return [self._normalize_paper(item) for item in data.get('data', [])]

    def _normalize_paper(self, item: dict) -> dict:
        paper_id = item.get('paperId', '')
        title = item.get('title', 'Untitled')
        abstract = item.get('abstract', '') or ''

        authors_list = [a.get('name', '') for a in item.get('authors', [])]
        year = item.get('year', '')

        oa_pdf = item.get('openAccessPdf')
        pdf_url = oa_pdf.get('url', '') if oa_pdf else ''

        ext_ids = item.get('externalIds', {}) or {}
        arxiv_id = ext_ids.get('ArXiv', '')
        if not pdf_url and arxiv_id:
            pdf_url = f'https://arxiv.org/pdf/{arxiv_id}'

        url = item.get('url', f'https://www.semanticscholar.org/paper/{paper_id}')
        citation_count = item.get('citationCount', 0)

        return {
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list),
            'summary': self._truncate_summary(abstract),
            'full_summary': abstract,
            'published': str(year) if year else '',
            'abstract_url': url,
            'pdf_url': pdf_url,
            'categories': [],
            'source': self.NAME,
            'source_name': self.DISPLAY_NAME,
            'citations': citation_count,
        }
