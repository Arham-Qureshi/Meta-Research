from services.providers.base import BaseAPIProvider
from utils import reconstruct_abstract

class OpenAlexProvider(BaseAPIProvider):
    NAME = 'openalex'
    DISPLAY_NAME = 'OpenAlex'
    BASE_URL = 'https://api.openalex.org/works'

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        params = {
            'search': query,
            'per_page': min(max_results, 25),
            'sort': 'relevance_score:desc',
            'mailto': 'metaresearch@example.com',
            'select': (
                'id,doi,title,authorships,publication_date,primary_location,'
                'open_access,abstract_inverted_index,cited_by_count,concepts,type'
            ),
        }
        resp = self._get(self.BASE_URL, params=params)
        data = self._safe_json(resp)

        return [self._normalize_paper(item) for item in data.get('results', [])]

    def _normalize_paper(self, item: dict) -> dict:
        title = item.get('title', 'Untitled') or 'Untitled'

        authors_list = [
            a.get('author', {}).get('display_name', '')
            for a in item.get('authorships', [])[:10]
            if a.get('author', {}).get('display_name')
        ]

        abstract = ''
        inverted = item.get('abstract_inverted_index')
        if inverted:
            abstract = reconstruct_abstract(inverted)

        published_date = (item.get('publication_date', '') or '')[:10]

        pdf_url = ''
        oa_info = item.get('open_access', {})
        if oa_info.get('oa_url'):
            pdf_url = oa_info['oa_url']

        primary_loc = item.get('primary_location', {}) or {}
        landing_url = primary_loc.get('landing_page_url', '')
        doi_raw = item.get('doi', '') or ''
        doi_id = doi_raw.replace('https://doi.org/', '') if doi_raw else ''
        if not landing_url and doi_raw:
            landing_url = doi_raw

        openalex_id = item.get('id', '')
        paper_id = doi_id if doi_id else openalex_id

        concepts = item.get('concepts', [])
        categories = [c.get('display_name', '') for c in concepts[:5] if c.get('display_name')]

        source_info = primary_loc.get('source', {}) or {}
        journal = source_info.get('display_name', '')

        return {
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list),
            'summary': self._truncate_summary(abstract),
            'full_summary': abstract,
            'published': published_date,
            'abstract_url': landing_url,
            'pdf_url': pdf_url,
            'categories': categories,
            'source': self.NAME,
            'source_name': self.DISPLAY_NAME,
            'citations': item.get('cited_by_count', 0),
            'journal': journal,
        }
