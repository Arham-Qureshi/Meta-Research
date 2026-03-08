"""
news_service.py
Dual-API news aggregator with in-memory caching (5-hour TTL).
Sources: GNews API + NewsData.io  (both free tiers).
Falls back gracefully if either API key is missing or quota is hit.
"""

import os
import time
import requests
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────
GNEWS_API_KEY = os.environ.get('GNEWS_API_KEY', '')
NEWSDATA_API_KEY = os.environ.get('NEWSDATA_API_KEY', '')

GNEWS_URL = "https://gnews.io/api/v4/search"
NEWSDATA_URL = "https://newsdata.io/api/1/news"

CACHE_TTL_SECONDS = 5 * 60 * 60  # 5 hours

# ── In-memory cache ─────────────────────────────────────────────
_cache = {
    'news': {'data': [], 'ts': 0},
    'trending': {'data': [], 'ts': 0},
}


def _is_fresh(key: str) -> bool:
    return (time.time() - _cache[key]['ts']) < CACHE_TTL_SECONDS


# ── GNews fetcher ───────────────────────────────────────────────
def _fetch_gnews(query: str = "scientific research OR Nobel Prize OR technology breakthrough",
                 max_articles: int = 10) -> list[dict]:
    if not GNEWS_API_KEY:
        return []

    params = {
        'q': query,
        'lang': 'en',
        'max': min(max_articles, 10),
        'apikey': GNEWS_API_KEY,
        'sortby': 'publishedAt',
    }

    try:
        resp = requests.get(GNEWS_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[GNews] Request failed: {e}")
        return []

    articles = []
    for item in data.get('articles', []):
        articles.append({
            'title': item.get('title', ''),
            'description': item.get('description', ''),
            'url': item.get('url', ''),
            'image': item.get('image', ''),
            'published': item.get('publishedAt', ''),
            'source_name': item.get('source', {}).get('name', 'Unknown'),
            'provider': 'gnews',
        })
    return articles


# ── NewsData.io fetcher ─────────────────────────────────────────
def _fetch_newsdata(query: str = "research OR Nobel Prize OR science breakthrough",
                    max_articles: int = 10) -> list[dict]:
    if not NEWSDATA_API_KEY:
        return []

    params = {
        'q': query,
        'language': 'en',
        'category': 'science,technology',
        'apikey': NEWSDATA_API_KEY,
    }

    try:
        resp = requests.get(NEWSDATA_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[NewsData] Request failed: {e}")
        return []

    articles = []
    for item in data.get('results', [])[:max_articles]:
        articles.append({
            'title': item.get('title', ''),
            'description': item.get('description', '') or '',
            'url': item.get('link', ''),
            'image': item.get('image_url', '') or '',
            'published': item.get('pubDate', ''),
            'source_name': item.get('source_id', 'Unknown'),
            'provider': 'newsdata',
        })
    return articles


# ── Merge + dedupe by title similarity ──────────────────────────
def _merge_articles(a_list: list[dict], b_list: list[dict]) -> list[dict]:
    """Merge two article lists, removing near-duplicate titles."""
    seen_titles = set()
    merged = []

    for article in a_list + b_list:
        title_key = article.get('title', '').lower().strip()[:60]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            merged.append(article)

    # Sort by published date descending
    merged.sort(key=lambda x: x.get('published', ''), reverse=True)
    return merged


# ── Public API ──────────────────────────────────────────────────
def get_science_news(query: str = None, force_refresh: bool = False) -> list[dict]:
    """
    Returns a list of recent science/research news articles.
    Results are cached for 5 hours to respect API rate limits.
    """
    if not force_refresh and _is_fresh('news'):
        return _cache['news']['data']

    q = query or "scientific research OR Nobel Prize OR technology breakthrough"

    gnews_articles = _fetch_gnews(q)
    newsdata_articles = _fetch_newsdata(q)

    merged = _merge_articles(gnews_articles, newsdata_articles)

    # Update cache
    _cache['news'] = {'data': merged, 'ts': time.time()}
    return merged


def get_trending_papers(max_results: int = 12) -> list[dict]:
    """
    Fetch trending/popular recent papers using OpenAlex API.
    Returns papers published in the last 30 days sorted by citation count.
    Cached for 5 hours.
    """
    if _is_fresh('trending'):
        return _cache['trending']['data']

    from datetime import timedelta

    now = datetime.utcnow()
    from_date = (now - timedelta(days=60)).strftime('%Y-%m-%d')

    params = {
        'filter': f'from_publication_date:{from_date},type:article,has_abstract:true',
        'sort': 'cited_by_count:desc',
        'per_page': min(max_results, 25),
        'mailto': 'metaresearch@example.com',
        'select': 'id,doi,title,authorships,publication_date,primary_location,'
                  'open_access,abstract_inverted_index,cited_by_count,concepts,type',
    }

    try:
        resp = requests.get("https://api.openalex.org/works", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Trending] OpenAlex request failed: {e}")
        _cache['trending'] = {'data': [], 'ts': time.time()}
        return []

    papers = []
    for item in data.get('results', []):
        title = item.get('title', 'Untitled') or 'Untitled'

        authorships = item.get('authorships', [])
        authors = [a.get('author', {}).get('display_name', '')
                   for a in authorships[:5] if a.get('author', {}).get('display_name')]

        abstract = ''
        inv_idx = item.get('abstract_inverted_index')
        if inv_idx:
            positions = []
            for word, idxs in inv_idx.items():
                for pos in idxs:
                    positions.append((pos, word))
            positions.sort()
            abstract = ' '.join(w for _, w in positions)

        doi = item.get('doi', '') or ''
        doi_id = doi.replace('https://doi.org/', '') if doi.startswith('https://doi.org/') else doi

        primary_loc = item.get('primary_location', {}) or {}
        landing_url = primary_loc.get('landing_page_url', '') or doi or ''

        oa = item.get('open_access', {}) or {}
        pdf_url = oa.get('oa_url', '') or ''

        concepts = item.get('concepts', [])
        categories = [c.get('display_name', '') for c in concepts[:4] if c.get('display_name')]

        source_info = primary_loc.get('source', {}) or {}
        journal = source_info.get('display_name', '')

        papers.append({
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
            'journal': journal,
            'source': 'openalex',
            'source_name': 'OpenAlex',
        })

    _cache['trending'] = {'data': papers, 'ts': time.time()}
    return papers
