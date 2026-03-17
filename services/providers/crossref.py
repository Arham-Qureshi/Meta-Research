import re
from services.providers.base import BaseAPIProvider

class CrossrefProvider(BaseAPIProvider):
    NAME = 'crossref'
    DISPLAY_NAME = 'Crossref'
    BASE_URL = 'https://api.crossref.org/works'
    HEADERS = {
        'User-Agent': 'MetaResearch/1.0 (Academic Research Tool; mailto:metaresearch@example.com)',
    }

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        params = {
            'query': query,
            'rows': min(max_results, 20),
            'sort': 'relevance',
            'order': 'desc',
            'select': (
                'DOI,title,author,abstract,published-print,published-online,'
                'container-title,subject,link,URL,is-referenced-by-count'
            ),
        }
        resp = self._get(self.BASE_URL, params=params)
        data = self._safe_json(resp)

        items = data.get('message', {}).get('items', [])
        return [self._normalize_paper(item) for item in items]

    def _normalize_paper(self, item: dict) -> dict:
        title_list = item.get('title', [])
        title = title_list[0] if title_list else 'Untitled'

        authors_list = self._parse_authors(item.get('author', []))

        abstract = item.get('abstract', '') or ''
        abstract = re.sub(r'<[^>]+>', '', abstract).strip()

        published_date = self._parse_date(item)
        doi = item.get('DOI', '')
        url = item.get('URL', f'https://doi.org/{doi}' if doi else '')
        pdf_url = self._find_pdf(item, doi)

        container = item.get('container-title', [])
        journal = container[0] if container else ''
        subjects = item.get('subject', [])
        paper_id = doi if doi else f'crossref-{hash(title)}'
        citation_count = item.get('is-referenced-by-count', 0)

        return {
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list[:10]),
            'summary': self._truncate_summary(abstract),
            'full_summary': abstract,
            'published': published_date,
            'abstract_url': url,
            'pdf_url': pdf_url,
            'categories': subjects[:5],
            'source': self.NAME,
            'source_name': self.DISPLAY_NAME,
            'citations': citation_count,
            'journal': journal,
        }

    @staticmethod
    def _parse_authors(raw_authors: list) -> list[str]:
        names = []
        for a in raw_authors:
            given = a.get('given', '')
            family = a.get('family', '')
            name = f'{given} {family}'.strip()
            if name:
                names.append(name)
        return names

    @staticmethod
    def _parse_date(item: dict) -> str:
        for field in ('published-print', 'published-online'):
            date_info = item.get(field)
            if date_info and date_info.get('date-parts'):
                parts = [str(p) for p in date_info['date-parts'][0] if p]
                if len(parts) >= 3:
                    return f'{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}'
                if parts:
                    return parts[0]
        return ''

    @staticmethod
    def _find_pdf(item: dict, doi: str) -> str:
        for link in item.get('link', []):
            if link.get('content-type') == 'application/pdf':
                return link.get('URL', '')
        return f'https://doi.org/{doi}' if doi else ''
