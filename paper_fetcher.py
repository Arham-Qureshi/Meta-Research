import requests
from bs4 import BeautifulSoup
import time
import re
ARXIV_API_URL = "http://export.arxiv.org/api/query"

def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    params = {
        'search_query': f'all:{query}',
        'start': 0,
        'max_results': max_results,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    headers = {
        'User-Agent': 'MetaResearch/1.0 (Academic Research Tool)'
    }

    try:
        response = requests.get(ARXIV_API_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()  # Raise error for bad status codes (4xx, 5xx)
    except requests.RequestException as e:
        print(f"[ArXiv] Request failed: {e}")
        return []
    soup = BeautifulSoup(response.text, 'lxml-xml')
    entries = soup.find_all('entry')
    papers = []
    for entry in entries:
        arxiv_id_raw = entry.find('id').text.strip()
        arxiv_id = arxiv_id_raw.split('/abs/')[-1] if '/abs/' in arxiv_id_raw else arxiv_id_raw

        title = entry.find('title').text.strip().replace('\n', ' ')
        summary = entry.find('summary').text.strip().replace('\n', ' ')
        authors = [a.find('name').text.strip() for a in entry.find_all('author')]
        published = entry.find('published')
        published_date = published.text.strip()[:10] if published else ''
        link_tag = entry.find('link', {'rel': 'alternate'})
        abstract_url = link_tag['href'] if link_tag else arxiv_id_raw
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        categories = [cat.get('term', '') for cat in entry.find_all('category')]

        papers.append({
            'id': arxiv_id,
            'title': title,
            'authors': ', '.join(authors),
            'summary': summary[:500] + ('...' if len(summary) > 500 else ''),
            'full_summary': summary,
            'published': published_date,
            'abstract_url': abstract_url,
            'pdf_url': pdf_url,
            'categories': categories,
            'source': 'arxiv',
            'source_name': 'ArXiv'
        })

    return papers

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    params = {
        'query': query,
        'limit': min(max_results, 20),
        'fields': 'title,authors,abstract,year,externalIds,openAccessPdf,url,citationCount'
    }
    headers = {
        'User-Agent': 'MetaResearch/1.0 (Academic Research Tool)'
    }

    try:
        response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[SemanticScholar] Request failed: {e}")
        return []
    except ValueError:
        print("[SemanticScholar] Invalid JSON response")
        return []

    papers = []
    for item in data.get('data', []):
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
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        url = item.get('url', f"https://www.semanticscholar.org/paper/{paper_id}")
        citation_count = item.get('citationCount', 0)

        papers.append({
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list),
            'summary': abstract[:500] + ('...' if len(abstract) > 500 else ''),
            'full_summary': abstract,
            'published': str(year) if year else '',
            'abstract_url': url,
            'pdf_url': pdf_url,
            'categories': [],
            'source': 'semantic_scholar',
            'source_name': 'Semantic Scholar',
            'citations': citation_count
        })

    return papers

CROSSREF_API_URL = "https://api.crossref.org/works"

def search_crossref(query: str, max_results: int = 10) -> list[dict]:
    params = {
        'query': query,
        'rows': min(max_results, 20),
        'sort': 'relevance',
        'order': 'desc',
        'select': 'DOI,title,author,abstract,published-print,published-online,'
                  'container-title,subject,link,URL'
    }
    headers = {
        'User-Agent': 'MetaResearch/1.0 (Academic Research Tool; mailto:metaresearch@example.com)'
    }

    try:
        response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[Crossref] Request failed: {e}")
        return []
    except ValueError:
        print("[Crossref] Invalid JSON response")
        return []

    papers = []
    items = data.get('message', {}).get('items', [])

    for item in items:
        title_list = item.get('title', [])
        title = title_list[0] if title_list else 'Untitled'
        authors_raw = item.get('author', [])
        authors_list = []
        for a in authors_raw:
            given = a.get('given', '')
            family = a.get('family', '')
            name = f"{given} {family}".strip()
            if name:
                authors_list.append(name)

        abstract = item.get('abstract', '') or ''
        abstract = re.sub(r'<[^>]+>', '', abstract).strip()
        date_parts = None
        for date_field in ('published-print', 'published-online'):
            date_info = item.get(date_field)
            if date_info and date_info.get('date-parts'):
                date_parts = date_info['date-parts'][0]
                break

        published_date = ''
        if date_parts:
            parts = [str(p) for p in date_parts if p]
            if len(parts) >= 3:
                published_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            elif len(parts) >= 1:
                published_date = parts[0]
        doi = item.get('DOI', '')
        url = item.get('URL', f"https://doi.org/{doi}" if doi else '')
        pdf_url = ''
        links = item.get('link', [])
        for link in links:
            if link.get('content-type') == 'application/pdf':
                pdf_url = link.get('URL', '')
                break
        if not pdf_url and doi:
            pdf_url = f"https://doi.org/{doi}"

        container = item.get('container-title', [])
        journal = container[0] if container else ''
        subjects = item.get('subject', [])
        paper_id = doi if doi else f"crossref-{hash(title)}"

        papers.append({
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list[:10]),  # Limit to 10 authors
            'summary': abstract[:500] + ('...' if len(abstract) > 500 else ''),
            'full_summary': abstract,
            'published': published_date,
            'abstract_url': url,
            'pdf_url': pdf_url,
            'categories': subjects[:5],
            'source': 'crossref',
            'source_name': 'Crossref',
            'journal': journal
        })

    return papers

OPENALEX_API_URL = "https://api.openalex.org/works"

def search_openalex(query: str, max_results: int = 10) -> list[dict]:
    params = {
        'search': query,
        'per_page': min(max_results, 25),
        'sort': 'relevance_score:desc',
        'mailto': 'metaresearch@example.com',
        'select': 'id,doi,title,authorships,publication_date,primary_location,'
                  'open_access,abstract_inverted_index,cited_by_count,concepts,type'
    }

    try:
        response = requests.get(OPENALEX_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[OpenAlex] Request failed: {e}")
        return []
    except ValueError:
        print("[OpenAlex] Invalid JSON response")
        return []

    papers = []
    results = data.get('results', [])

    for item in results:
        title = item.get('title', 'Untitled') or 'Untitled'
        authorships = item.get('authorships', [])
        authors_list = []
        for authorship in authorships[:10]:
            author_info = authorship.get('author', {})
            name = author_info.get('display_name', '')
            if name:
                authors_list.append(name)

        abstract = ''
        abstract_index = item.get('abstract_inverted_index')
        if abstract_index:
            abstract = _reconstruct_abstract(abstract_index)
        published_date = item.get('publication_date', '') or ''
        if published_date and len(published_date) >= 10:
            published_date = published_date[:10]
        pdf_url = ''
        oa_info = item.get('open_access', {})
        oa_url = oa_info.get('oa_url', '')
        if oa_url:
            pdf_url = oa_url
        primary_loc = item.get('primary_location', {}) or {}
        landing_url = primary_loc.get('landing_page_url', '')
        doi = item.get('doi', '') or ''
        if doi and doi.startswith('https://doi.org/'):
            doi_id = doi.replace('https://doi.org/', '')
        else:
            doi_id = doi
        if not landing_url and doi:
            landing_url = doi
        openalex_id = item.get('id', '')
        paper_id = doi_id if doi_id else openalex_id
        concepts = item.get('concepts', [])
        categories = [c.get('display_name', '') for c in concepts[:5] if c.get('display_name')]
        citation_count = item.get('cited_by_count', 0)
        source_info = primary_loc.get('source', {}) or {}
        journal = source_info.get('display_name', '')

        papers.append({
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list),
            'summary': abstract[:500] + ('...' if len(abstract) > 500 else ''),
            'full_summary': abstract,
            'published': published_date,
            'abstract_url': landing_url,
            'pdf_url': pdf_url,
            'categories': categories,
            'source': 'openalex',
            'source_name': 'OpenAlex',
            'citations': citation_count,
            'journal': journal
        })

    return papers


def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ''
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return ' '.join(word for _, word in word_positions)



# ═══════════════════════════════════════════════════════════════
#  CITATION GRAPH  –  Uses paper IDs (not text search)
# ═══════════════════════════════════════════════════════════════

SEMANTIC_SCHOLAR_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"

# Rate-limit tracker for Semantic Scholar (100 req/5 min on free tier)
_ss_last_request_time = 0
_SS_MIN_INTERVAL = 1.1  # seconds between requests


def _ss_rate_limit():
    """Enforce minimum interval between Semantic Scholar API calls."""
    global _ss_last_request_time
    elapsed = time.time() - _ss_last_request_time
    if elapsed < _SS_MIN_INTERVAL:
        time.sleep(_SS_MIN_INTERVAL - elapsed)
    _ss_last_request_time = time.time()


def _resolve_paper_id(paper_id: str) -> str:
    """
    Normalise a paper ID for the Semantic Scholar API.
    Accepts: arXiv ID, DOI, Semantic Scholar ID, or OpenAlex ID.
    Returns the identifier prefixed appropriately.
    """
    pid = paper_id.strip()

    # Already a Semantic Scholar 40-char hex ID
    if len(pid) == 40 and all(c in '0123456789abcdef' for c in pid.lower()):
        return pid

    # DOI  (e.g. 10.1234/...)
    if pid.startswith('10.') or pid.startswith('doi:'):
        doi = pid.replace('doi:', '')
        return f"DOI:{doi}"

    # ArXiv  (e.g. 2301.12345 or arXiv:2301.12345)
    arxiv_match = re.match(r'^(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)$', pid)
    if arxiv_match:
        return f"ArXiv:{arxiv_match.group(1)}"

    # OpenAlex URL → strip to just the ID portion
    if pid.startswith('https://openalex.org/'):
        return pid  # Semantic Scholar won't accept this, try DOI fallback

    # Fallback: send as-is (Semantic Scholar will try to resolve)
    return pid


def get_citation_graph(paper_id: str, max_citations: int = 15, max_references: int = 15) -> dict:
    """
    Fetch the citation network for a given paper using Semantic Scholar
    paper-detail API (ID-based, NOT text search).

    Returns {
        'center': { id, title, authors, year, citationCount },
        'nodes':  [ { id, label, year, citations, type } ],
        'edges':  [ { source, target } ],
        'error':  str | None
    }
    """
    resolved_id = _resolve_paper_id(paper_id)
    fields = 'title,authors,year,citationCount,citations.title,citations.authors,citations.year,citations.citationCount,references.title,references.authors,references.year,references.citationCount'

    _ss_rate_limit()

    headers = {'User-Agent': 'MetaResearch/1.0 (Academic Research Tool)'}

    try:
        url = f"{SEMANTIC_SCHOLAR_PAPER_URL}/{resolved_id}"
        params = {
            'fields': fields,
            'limit': max(max_citations, max_references),
        }
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {'center': None, 'nodes': [], 'edges': [], 'error': f'API request failed: {str(e)}'}
    except ValueError:
        return {'center': None, 'nodes': [], 'edges': [], 'error': 'Invalid API response'}

    # ── Build center node ───────────────────────────────────────
    center_id = data.get('paperId', paper_id)
    center_authors = [a.get('name', '') for a in data.get('authors', [])[:3]]
    center = {
        'id': center_id,
        'title': data.get('title', 'Unknown'),
        'authors': ', '.join(center_authors),
        'year': data.get('year'),
        'citationCount': data.get('citationCount', 0),
    }

    nodes = [{
        'id': center_id,
        'label': center['title'],
        'year': center['year'],
        'citations': center['citationCount'],
        'type': 'center',
        'authors': center['authors'],
    }]
    edges = []
    seen_ids = {center_id}

    # ── Citations (papers that cite THIS paper) ────────────────
    for cite in data.get('citations', [])[:max_citations]:
        cid = cite.get('paperId')
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        c_authors = [a.get('name', '') for a in cite.get('authors', [])[:2]]
        nodes.append({
            'id': cid,
            'label': cite.get('title', 'Untitled'),
            'year': cite.get('year'),
            'citations': cite.get('citationCount', 0),
            'type': 'citation',
            'authors': ', '.join(c_authors),
        })
        edges.append({'source': cid, 'target': center_id})

    # ── References (papers THIS paper cites) ───────────────────
    for ref in data.get('references', [])[:max_references]:
        rid = ref.get('paperId')
        if not rid or rid in seen_ids:
            continue
        seen_ids.add(rid)
        r_authors = [a.get('name', '') for a in ref.get('authors', [])[:2]]
        nodes.append({
            'id': rid,
            'label': ref.get('title', 'Untitled'),
            'year': ref.get('year'),
            'citations': ref.get('citationCount', 0),
            'type': 'reference',
            'authors': ', '.join(r_authors),
        })
        edges.append({'source': center_id, 'target': rid})

    return {'center': center, 'nodes': nodes, 'edges': edges, 'error': None}


def search_papers(query: str, source: str = 'all', max_results: int = 10) -> list[dict]:
    results = []

    if source in ('arxiv', 'all'):
        results.extend(search_arxiv(query, max_results))

    if source in ('semantic_scholar', 'all'):
        if source == 'all':
            time.sleep(0.3)
        results.extend(search_semantic_scholar(query, max_results))

    if source in ('crossref', 'all'):
        if source == 'all':
            time.sleep(0.3)
        results.extend(search_crossref(query, max_results))

    if source in ('openalex', 'all'):
        if source == 'all':
            time.sleep(0.3)
        results.extend(search_openalex(query, max_results))

    return results
