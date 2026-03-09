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
            'source_name': 'ArXiv',
            'citations': 0
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
                  'container-title,subject,link,URL,is-referenced-by-count'
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

        citation_count = item.get('is-referenced-by-count', 0)
        papers.append({
            'id': paper_id,
            'title': title,
            'authors': ', '.join(authors_list[:10]),
            'summary': abstract[:500] + ('...' if len(abstract) > 500 else ''),
            'full_summary': abstract,
            'published': published_date,
            'abstract_url': url,
            'pdf_url': pdf_url,
            'categories': subjects[:5],
            'source': 'crossref',
            'source_name': 'Crossref',
            'citations': citation_count,
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
_SS_MIN_INTERVAL = 1.5  # seconds between requests (stay well within 100 req/5min)


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


def get_citation_graph(paper_id: str, max_citations: int = 20, max_references: int = 20,
                       source: str = 'semantic_scholar') -> dict:
    """
    Fetch citation network from the user's chosen source. No automatic fallback.
    All responses are strict JSON.

    Returns {
        'center': { id, title, authors, year, citationCount, doi },
        'nodes':  [ { id, label, year, citations, type, authors } ],
        'edges':  [ { source, target } ],
        'source': 'semantic_scholar' | 'openalex',
        'error':  str | None
    }
    """
    if source == 'openalex':
        return _graph_from_openalex(paper_id, max_citations, max_references)
    else:
        return _graph_from_semantic_scholar(paper_id, max_citations, max_references)


def _graph_from_semantic_scholar(paper_id: str, max_citations: int, max_references: int) -> dict:
    """Build citation graph from Semantic Scholar API (JSON)."""
    resolved_id = _resolve_paper_id(paper_id)
    fields = ('title,authors,year,citationCount,externalIds,'
              'citations.title,citations.authors,citations.year,citations.citationCount,citations.externalIds,'
              'references.title,references.authors,references.year,references.citationCount,references.externalIds')

    _ss_rate_limit()
    headers = {'User-Agent': 'MetaResearch/1.0 (Academic Research Tool)'}

    try:
        resp = requests.get(
            f"{SEMANTIC_SCHOLAR_PAPER_URL}/{resolved_id}",
            params={'fields': fields, 'limit': max(max_citations, max_references)},
            headers=headers, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        # On 429, try to get at least center node info from a lighter endpoint
        center_info = _ss_get_basic_info(resolved_id)
        return {'center': center_info, 'nodes': [], 'edges': [], 'source': 'semantic_scholar',
                'error': f'Semantic Scholar API failed: {str(e)}'}
    except ValueError:
        return {'center': None, 'nodes': [], 'edges': [], 'source': 'semantic_scholar',
                'error': 'Invalid JSON from Semantic Scholar'}

    return _build_graph_from_ss_data(data, paper_id, max_citations, max_references)


def _ss_get_basic_info(resolved_id: str) -> dict:
    """Try to get at least center paper DOI/title from a lightweight S.S. call."""
    _ss_rate_limit()
    try:
        resp = requests.get(
            f"{SEMANTIC_SCHOLAR_PAPER_URL}/{resolved_id}",
            params={'fields': 'title,externalIds,year,citationCount,authors'},
            headers={'User-Agent': 'MetaResearch/1.0'}, timeout=10
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                'id': d.get('paperId', ''), 'title': d.get('title', 'Unknown'),
                'authors': ', '.join(a.get('name', '') for a in d.get('authors', [])[:3]),
                'year': d.get('year'), 'citationCount': d.get('citationCount', 0),
                'doi': _extract_doi(d.get('externalIds')),
            }
    except Exception:
        pass
    return None


def _extract_doi(ext_ids):
    """Extract DOI from externalIds dict."""
    if not ext_ids:
        return ''
    return ext_ids.get('DOI', '') or ''


def _build_graph_from_ss_data(data, paper_id, max_citations, max_references):
    """Transform Semantic Scholar JSON into our graph format."""
    center_id = data.get('paperId', paper_id)
    center_authors = [a.get('name', '') for a in data.get('authors', [])[:3]]
    center_doi = _extract_doi(data.get('externalIds'))
    center = {
        'id': center_id,
        'title': data.get('title', 'Unknown'),
        'authors': ', '.join(center_authors),
        'year': data.get('year'),
        'citationCount': data.get('citationCount', 0),
        'doi': center_doi,
    }

    nodes = [{
        'id': center_id, 'label': center['title'], 'year': center['year'],
        'citations': center['citationCount'], 'type': 'center',
        'authors': center['authors'], 'doi': center_doi,
    }]
    edges = []
    seen_ids = {center_id}

    for cite in data.get('citations', [])[:max_citations]:
        cid = cite.get('paperId')
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        authors = ', '.join(a.get('name', '') for a in cite.get('authors', [])[:2])
        nodes.append({
            'id': cid, 'label': cite.get('title', 'Untitled'), 'year': cite.get('year'),
            'citations': cite.get('citationCount', 0), 'type': 'citation',
            'authors': authors, 'doi': _extract_doi(cite.get('externalIds')),
        })
        edges.append({'source': cid, 'target': center_id})

    for ref in data.get('references', [])[:max_references]:
        rid = ref.get('paperId')
        if not rid or rid in seen_ids:
            continue
        seen_ids.add(rid)
        authors = ', '.join(a.get('name', '') for a in ref.get('authors', [])[:2])
        nodes.append({
            'id': rid, 'label': ref.get('title', 'Untitled'), 'year': ref.get('year'),
            'citations': ref.get('citationCount', 0), 'type': 'reference',
            'authors': authors, 'doi': _extract_doi(ref.get('externalIds')),
        })
        edges.append({'source': center_id, 'target': rid})

    return {'center': center, 'nodes': nodes, 'edges': edges, 'source': 'semantic_scholar', 'error': None}


def _openalex_search_by_title(title: str) -> str:
    """Search OpenAlex by title, return the first matching OpenAlex ID or empty string."""
    try:
        resp = requests.get(
            OPENALEX_API_URL,
            params={'search': title, 'select': 'id', 'per_page': 1, 'mailto': 'metaresearch@example.com'},
            timeout=10
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
        if results:
            return results[0].get('id', '')
    except Exception:
        pass
    return ''


def _graph_from_openalex(paper_id: str, max_citations: int, max_references: int,
                         fallback_doi: str = '', fallback_title: str = '') -> dict:
    """Build citation graph from OpenAlex API (JSON). Fallback source."""
    # Resolve to OpenAlex-friendly identifier
    oa_id = paper_id.strip()

    # DOI format
    if oa_id.startswith('10.'):
        oa_id = f"https://doi.org/{oa_id}"
    # Semantic Scholar 40-char hex ID — OpenAlex can't use this directly
    elif len(oa_id) == 40 and all(c in '0123456789abcdef' for c in oa_id.lower()):
        # Try fallback DOI first
        if fallback_doi:
            oa_id = f"https://doi.org/{fallback_doi}"
        elif fallback_title:
            # Search by title to find the OpenAlex ID
            resolved = _openalex_search_by_title(fallback_title)
            if resolved:
                oa_id = resolved
            else:
                return {'center': None, 'nodes': [], 'edges': [], 'source': 'openalex',
                        'error': 'Cannot resolve Semantic Scholar ID for OpenAlex'}
        else:
            return {'center': None, 'nodes': [], 'edges': [], 'source': 'openalex',
                    'error': 'No DOI or title available for OpenAlex fallback'}

    fields = 'id,doi,title,authorships,publication_date,cited_by_count,referenced_works,cited_by_api_url'
    try:
        resp = requests.get(
            f"{OPENALEX_API_URL}/{oa_id}",
            params={'select': fields, 'mailto': 'metaresearch@example.com'},
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return {'center': None, 'nodes': [], 'edges': [], 'source': 'openalex',
                'error': 'OpenAlex API failed'}

    # Center node
    oa_center_id = data.get('id', '')
    doi_raw = data.get('doi', '') or ''
    doi = doi_raw.replace('https://doi.org/', '') if doi_raw else ''
    center_authors = ', '.join(
        a.get('author', {}).get('display_name', '') for a in data.get('authorships', [])[:3]
    )
    year_str = (data.get('publication_date') or '')[:4]
    year = int(year_str) if year_str.isdigit() else None

    center = {
        'id': oa_center_id, 'title': data.get('title', 'Unknown'),
        'authors': center_authors, 'year': year,
        'citationCount': data.get('cited_by_count', 0), 'doi': doi,
    }
    nodes = [{
        'id': oa_center_id, 'label': center['title'], 'year': year,
        'citations': center['citationCount'], 'type': 'center',
        'authors': center_authors, 'doi': doi,
    }]
    edges = []
    seen_ids = {oa_center_id}

    # References (papers this paper cites) — IDs are in referenced_works
    ref_ids = data.get('referenced_works', [])[:max_references]
    if ref_ids:
        ref_filter = '|'.join(ref_ids)
        try:
            rr = requests.get(
                OPENALEX_API_URL,
                params={
                    'filter': f'openalex:{ref_filter}',
                    'select': 'id,doi,title,authorships,publication_date,cited_by_count',
                    'per_page': max_references,
                    'mailto': 'metaresearch@example.com',
                },
                timeout=15
            )
            rr.raise_for_status()
            for item in rr.json().get('results', []):
                nid = item.get('id', '')
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                n_doi = (item.get('doi') or '').replace('https://doi.org/', '')
                n_year_str = (item.get('publication_date') or '')[:4]
                nodes.append({
                    'id': nid, 'label': item.get('title', 'Untitled'),
                    'year': int(n_year_str) if n_year_str.isdigit() else None,
                    'citations': item.get('cited_by_count', 0), 'type': 'reference',
                    'authors': ', '.join(a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])[:2]),
                    'doi': n_doi,
                })
                edges.append({'source': oa_center_id, 'target': nid})
        except (requests.RequestException, ValueError):
            pass  # partial graph is still useful

    # Citations (papers that cite this paper) — use cited_by_api_url
    cited_by_url = data.get('cited_by_api_url', '')
    if cited_by_url:
        try:
            cr = requests.get(
                cited_by_url,
                params={
                    'select': 'id,doi,title,authorships,publication_date,cited_by_count',
                    'per_page': max_citations,
                    'mailto': 'metaresearch@example.com',
                },
                timeout=15
            )
            cr.raise_for_status()
            for item in cr.json().get('results', []):
                nid = item.get('id', '')
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                n_doi = (item.get('doi') or '').replace('https://doi.org/', '')
                n_year_str = (item.get('publication_date') or '')[:4]
                nodes.append({
                    'id': nid, 'label': item.get('title', 'Untitled'),
                    'year': int(n_year_str) if n_year_str.isdigit() else None,
                    'citations': item.get('cited_by_count', 0), 'type': 'citation',
                    'authors': ', '.join(a.get('author', {}).get('display_name', '') for a in item.get('authorships', [])[:2]),
                    'doi': n_doi,
                })
                edges.append({'source': nid, 'target': oa_center_id})
        except (requests.RequestException, ValueError):
            pass

    return {'center': center, 'nodes': nodes, 'edges': edges, 'source': 'openalex', 'error': None}


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
