import os
import time
from datetime import datetime, timedelta
from services.base import BaseService
from utils import reconstruct_abstract

class NewsService(BaseService):

    GNEWS_URL = 'https://gnews.io/api/v4/search'
    NEWSDATA_URL = 'https://newsdata.io/api/1/news'
    OPENALEX_URL = 'https://api.openalex.org/works'
    CACHE_TTL = 5 * 60 * 60
    # refresh every 5 hours

    def __init__(self):
        self._gnews_key = os.environ.get('GNEWS_API_KEY', '')
        self._newsdata_key = os.environ.get('NEWSDATA_API_KEY', '')
        self._cache = {
            'news': {'data': [], 'ts': 0},
            'trending': {'data': [], 'ts': 0},
        }

    def get_news(self, query: str | None = None, force_refresh: bool = False) -> list[dict]:
        if not force_refresh and self._is_fresh('news'):
            return self._cache['news']['data']

        q = query or 'scientific research OR Nobel Prize OR technology breakthrough'
        gnews = self._fetch_gnews(q)
        newsdata = self._fetch_newsdata(q)
        merged = self._merge_articles(gnews, newsdata)

        self._cache['news'] = {'data': merged, 'ts': time.time()}
        return merged

    def get_trending(self, max_results: int = 12) -> list[dict]:
        if self._is_fresh('trending'):
            return self._cache['trending']['data']

        from_date = (datetime.utcnow() - timedelta(days=60)).strftime('%Y-%m-%d')
        params = {
            'filter': f'from_publication_date:{from_date},type:article,has_abstract:true',
            'sort': 'cited_by_count:desc',
            'per_page': min(max_results, 25),
            'mailto': 'metaresearch@example.com',
            'select': (
                'id,doi,title,authorships,publication_date,primary_location,'
                'open_access,abstract_inverted_index,cited_by_count,concepts,type'
            ),
        }

        resp = self._get(self.OPENALEX_URL, params=params)
        data = self._safe_json(resp)

        if not data:
            self._cache['trending'] = {'data': [], 'ts': time.time()}
            return []

        papers = [self._normalize_trending(item) for item in data.get('results', [])]
        self._cache['trending'] = {'data': papers, 'ts': time.time()}
        return papers

    def _is_fresh(self, key: str) -> bool:
        return (time.time() - self._cache[key]['ts']) < self.CACHE_TTL

    def _fetch_gnews(self, query: str, max_articles: int = 10) -> list[dict]:
        if not self._gnews_key:
            return []
        params = {
            'q': query, 'lang': 'en',
            'max': min(max_articles, 10),
            'apikey': self._gnews_key,
            'sortby': 'publishedAt',
        }
        resp = self._get(self.GNEWS_URL, params=params, timeout=12)
        data = self._safe_json(resp)
        return [
            {
                'title': a.get('title', ''),
                'description': a.get('description', ''),
                'url': a.get('url', ''),
                'image': a.get('image', ''),
                'published': a.get('publishedAt', ''),
                'source_name': a.get('source', {}).get('name', 'Unknown'),
                'provider': 'gnews',
            }
            for a in data.get('articles', [])
        ]

    def _fetch_newsdata(self, query: str, max_articles: int = 10) -> list[dict]:
        if not self._newsdata_key:
            return []
        params = {
            'q': query, 'language': 'en',
            'category': 'science,technology',
            'apikey': self._newsdata_key,
        }
        resp = self._get(self.NEWSDATA_URL, params=params, timeout=12)
        data = self._safe_json(resp)
        return [
            {
                'title': a.get('title', ''),
                'description': a.get('description', '') or '',
                'url': a.get('link', ''),
                'image': a.get('image_url', '') or '',
                'published': a.get('pubDate', ''),
                'source_name': a.get('source_id', 'Unknown'),
                'provider': 'newsdata',
            }
            for a in data.get('results', [])[:max_articles]
        ]

    @staticmethod
    def _merge_articles(a_list: list[dict], b_list: list[dict]) -> list[dict]:
        seen = set()
        merged = []
        for article in a_list + b_list:
            key = article.get('title', '').lower().strip()[:60]
            if key and key not in seen:
                seen.add(key)
                merged.append(article)
        merged.sort(key=lambda x: x.get('published', ''), reverse=True)
        return merged

    def _normalize_trending(self, item: dict) -> dict:
        title = item.get('title', 'Untitled') or 'Untitled'
        authorships = item.get('authorships', [])
        authors = [
            a.get('author', {}).get('display_name', '')
            for a in authorships[:5]
            if a.get('author', {}).get('display_name')
        ]

        abstract = ''
        inv = item.get('abstract_inverted_index')
        if inv:
            abstract = reconstruct_abstract(inv)

        doi_raw = item.get('doi', '') or ''
        doi_id = doi_raw.replace('https://doi.org/', '') if doi_raw.startswith('https://doi.org/') else doi_raw

        primary_loc = item.get('primary_location', {}) or {}
        landing_url = primary_loc.get('landing_page_url', '') or doi_raw or ''
        oa = item.get('open_access', {}) or {}
        pdf_url = oa.get('oa_url', '') or ''

        concepts = item.get('concepts', [])
        categories = [c.get('display_name', '') for c in concepts[:4] if c.get('display_name')]
        source_info = primary_loc.get('source', {}) or {}

        return {
            'id': doi_id or item.get('id', ''),
            'title': title,
            'authors': ', '.join(authors),
            'summary': abstract[:300] + ('...' if len(abstract) > 300 else ''),
            'full_summary': abstract,
            'published': item.get('publication_date', ''),
            'abstract_url': landing_url,
            'pdf_url': pdf_url,
            'categories': categories,
            'citations': item.get('cited_by_count', 0),
            'journal': source_info.get('display_name', ''),
            'source': 'openalex',
            'source_name': 'OpenAlex',
        }

news_service = NewsService()
