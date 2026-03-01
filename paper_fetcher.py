"""
paper_fetcher.py  –  Research Paper Fetching Module
====================================================

This module is responsible for searching and retrieving research papers from
external sources. It currently supports:

1. **ArXiv API** (primary, free, no authentication needed)
2. **Semantic Scholar API** (secondary, free, no key needed for basic usage)

HOW IT WORKS (Educational Guide – Web Scraping & API Fetching)
--------------------------------------------------------------
### What is an API vs Web Scraping?

**API (Application Programming Interface)**
  An API is a *structured* way a website lets you request data. You send a
  URL with parameters (like a search query) and the server returns data in a
  machine-readable format (XML, JSON). This is the *preferred* method because
  it is fast, reliable, and officially supported.

  Example: ArXiv provides a free API at http://export.arxiv.org/api/query
  You call it like:
    http://export.arxiv.org/api/query?search_query=all:machine+learning&max_results=10

**Web Scraping**
  Web scraping means downloading the raw HTML of a webpage and *parsing* it
  to extract the data you need. You use a library like `requests` to download
  the page and `BeautifulSoup` to navigate the HTML tree.

  This is useful when a site does NOT have an API but still has public data.

### How the ArXiv API works (step by step)

1. **Build the URL** – We construct a URL with query parameters:
   - `search_query`: The user's search terms
   - `start`: Pagination offset
   - `max_results`: How many papers to return
   - `sortBy`: How to sort (relevance, date)

2. **Send the HTTP Request** – We use Python's `requests.get(url)` to send
   an HTTP GET request to ArXiv's server. This is identical to what your
   browser does when you visit a webpage.

3. **Parse the XML Response** – ArXiv returns data in Atom XML format.
   We use BeautifulSoup with the 'lxml-xml' parser to navigate the XML tree
   and extract <entry> elements (each entry = one paper).

4. **Extract Fields** – For each <entry>, we pull out:
   - `<title>` → paper title
   - `<summary>` → abstract / description
   - `<author><name>` → list of authors
   - `<link rel="alternate">` → link to the paper page
   - `<id>` → unique ArXiv identifier
   - PDF link → derived from the ID (e.g., http://arxiv.org/pdf/2301.12345)

5. **Return Structured Data** – We return a list of dictionaries, each
   containing all the fields above, ready for the frontend to display.

### How BeautifulSoup works (Web Scraping basics)

BeautifulSoup turns messy HTML/XML into a navigable tree:

```python
from bs4 import BeautifulSoup

html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
soup = BeautifulSoup(html, 'html.parser')

# Find a tag
soup.find('h1')           # → <h1>Hello</h1>
soup.find('h1').text      # → "Hello"

# Find all tags of a type
soup.find_all('p')        # → [<p>World</p>]

# Navigate with CSS selectors
soup.select('body > p')   # → [<p>World</p>]
```

Key BeautifulSoup methods:
  - `soup.find(tag)` – find the FIRST matching tag
  - `soup.find_all(tag)` – find ALL matching tags
  - `tag.text` or `tag.get_text()` – get the text inside a tag
  - `tag['attribute']` or `tag.get('attribute')` – get an attribute value
  - `soup.select('css selector')` – use CSS selectors to find elements

### Edge Cases & Best Practices

1. **Rate Limiting** – Don't hammer APIs. ArXiv asks for max 1 request
   every 3 seconds. We add a small delay between requests.
2. **Error Handling** – Network errors happen. We wrap requests in
   try/except blocks and return empty results on failure.
3. **Timeouts** – We set a timeout on requests so the app doesn't hang.
4. **User-Agent Header** – Some websites block requests without a browser
   User-Agent header. We send one to be polite.

"""

import requests
from bs4 import BeautifulSoup
import time
import re


# ---------------------------------------------------------------------------
# ArXiv API Search
# ---------------------------------------------------------------------------

ARXIV_API_URL = "http://export.arxiv.org/api/query"

def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    """
    Search ArXiv for papers matching the query.

    HOW THIS WORKS:
    1. We URL-encode the query and build the API URL.
    2. We send an HTTP GET request to ArXiv.
    3. ArXiv returns XML; we parse it with BeautifulSoup.
    4. We loop through <entry> tags and extract paper info.
    5. We derive the PDF URL from the paper's ArXiv ID.

    Args:
        query: Search terms (e.g., "machine learning")
        max_results: Maximum number of papers to return

    Returns:
        A list of dicts, each containing paper metadata.
    """
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
        # Step 1: Send the HTTP GET request
        response = requests.get(ARXIV_API_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()  # Raise error for bad status codes (4xx, 5xx)
    except requests.RequestException as e:
        print(f"[ArXiv] Request failed: {e}")
        return []

    # Step 2: Parse the XML response with BeautifulSoup
    soup = BeautifulSoup(response.text, 'lxml-xml')

    # Step 3: Find all <entry> tags (each = one paper)
    entries = soup.find_all('entry')

    papers = []
    for entry in entries:
        # Step 4: Extract each field from the XML entry
        arxiv_id_raw = entry.find('id').text.strip()
        # The ArXiv ID looks like "http://arxiv.org/abs/2301.12345v1"
        # We extract just the ID portion
        arxiv_id = arxiv_id_raw.split('/abs/')[-1] if '/abs/' in arxiv_id_raw else arxiv_id_raw

        title = entry.find('title').text.strip().replace('\n', ' ')
        summary = entry.find('summary').text.strip().replace('\n', ' ')

        # Authors: each <author> tag contains a <name> tag
        authors = [a.find('name').text.strip() for a in entry.find_all('author')]

        # Published date
        published = entry.find('published')
        published_date = published.text.strip()[:10] if published else ''

        # Link to the abstract page
        link_tag = entry.find('link', {'rel': 'alternate'})
        abstract_url = link_tag['href'] if link_tag else arxiv_id_raw

        # PDF URL: ArXiv PDFs follow a predictable pattern
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        # Categories / tags
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


# ---------------------------------------------------------------------------
# Semantic Scholar API Search
# ---------------------------------------------------------------------------

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Semantic Scholar for papers matching the query.

    HOW THIS WORKS:
    1. We build a request to the Semantic Scholar API.
    2. The API returns JSON (structured data, much easier than XML).
    3. We extract paper metadata including open-access PDF links.

    Semantic Scholar is great because it often provides direct PDF links
    even for papers not on ArXiv.
    """
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

        # Semantic Scholar provides open access PDF info
        oa_pdf = item.get('openAccessPdf')
        pdf_url = oa_pdf.get('url', '') if oa_pdf else ''

        # Try to get ArXiv ID if available
        ext_ids = item.get('externalIds', {}) or {}
        arxiv_id = ext_ids.get('ArXiv', '')

        # If no open access PDF but has ArXiv ID, construct ArXiv PDF URL
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


# ---------------------------------------------------------------------------
# Crossref API Search
# ---------------------------------------------------------------------------

CROSSREF_API_URL = "https://api.crossref.org/works"

def search_crossref(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Crossref for papers matching the query.

    HOW THIS WORKS:
    1. We query the Crossref REST API which indexes 150M+ scholarly works.
    2. The API returns JSON with metadata about journal articles, conference
       papers, books, and more.
    3. Crossref is the official DOI registration agency, so it has the most
       authoritative metadata for published works.
    4. No API key needed – we just add a mailto header for the "polite pool"
       which gives us faster response times.

    Args:
        query: Search terms (e.g., "machine learning")
        max_results: Maximum number of papers to return

    Returns:
        A list of dicts, each containing paper metadata.
    """
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
        # Title: Crossref returns title as a list
        title_list = item.get('title', [])
        title = title_list[0] if title_list else 'Untitled'

        # Authors
        authors_raw = item.get('author', [])
        authors_list = []
        for a in authors_raw:
            given = a.get('given', '')
            family = a.get('family', '')
            name = f"{given} {family}".strip()
            if name:
                authors_list.append(name)

        # Abstract: Crossref provides it as raw XML/HTML sometimes
        abstract = item.get('abstract', '') or ''
        # Strip basic HTML/XML tags from abstract
        abstract = re.sub(r'<[^>]+>', '', abstract).strip()

        # Publication date
        date_parts = None
        for date_field in ('published-print', 'published-online'):
            date_info = item.get(date_field)
            if date_info and date_info.get('date-parts'):
                date_parts = date_info['date-parts'][0]
                break

        published_date = ''
        if date_parts:
            # date_parts is like [2023, 5, 15] or [2023, 5] or [2023]
            parts = [str(p) for p in date_parts if p]
            if len(parts) >= 3:
                published_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            elif len(parts) >= 1:
                published_date = parts[0]

        # DOI and URLs
        doi = item.get('DOI', '')
        url = item.get('URL', f"https://doi.org/{doi}" if doi else '')

        # Try to find a direct PDF link
        pdf_url = ''
        links = item.get('link', [])
        for link in links:
            if link.get('content-type') == 'application/pdf':
                pdf_url = link.get('URL', '')
                break
        # Fallback: Sci-Hub style or DOI link
        if not pdf_url and doi:
            pdf_url = f"https://doi.org/{doi}"

        # Journal / container
        container = item.get('container-title', [])
        journal = container[0] if container else ''

        # Subjects / categories
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


# ---------------------------------------------------------------------------
# OpenAlex API Search
# ---------------------------------------------------------------------------

OPENALEX_API_URL = "https://api.openalex.org/works"

def search_openalex(query: str, max_results: int = 10) -> list[dict]:
    """
    Search OpenAlex for papers matching the query.

    HOW THIS WORKS:
    1. OpenAlex is a fully open catalog of the global research system,
       indexing 250M+ works from all disciplines.
    2. The API is completely free, requires no key, and returns JSON.
    3. It provides excellent open-access PDF links and citation data.
    4. We add a mailto parameter for the "polite pool" (faster responses).

    Args:
        query: Search terms (e.g., "deep learning")
        max_results: Maximum number of papers to return

    Returns:
        A list of dicts, each containing paper metadata.
    """
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

        # Authors: OpenAlex uses 'authorships' with nested author info
        authorships = item.get('authorships', [])
        authors_list = []
        for authorship in authorships[:10]:
            author_info = authorship.get('author', {})
            name = author_info.get('display_name', '')
            if name:
                authors_list.append(name)

        # Abstract: OpenAlex stores it as an "inverted index"
        # We need to reconstruct it from the inverted index
        abstract = ''
        abstract_index = item.get('abstract_inverted_index')
        if abstract_index:
            abstract = _reconstruct_abstract(abstract_index)

        # Publication date
        published_date = item.get('publication_date', '') or ''
        if published_date and len(published_date) >= 10:
            published_date = published_date[:10]

        # Open Access PDF
        pdf_url = ''
        oa_info = item.get('open_access', {})
        oa_url = oa_info.get('oa_url', '')
        if oa_url:
            pdf_url = oa_url

        # Primary location for the article page URL
        primary_loc = item.get('primary_location', {}) or {}
        landing_url = primary_loc.get('landing_page_url', '')

        # DOI
        doi = item.get('doi', '') or ''
        if doi and doi.startswith('https://doi.org/'):
            doi_id = doi.replace('https://doi.org/', '')
        else:
            doi_id = doi

        # If no landing URL, use DOI link
        if not landing_url and doi:
            landing_url = doi

        # OpenAlex ID
        openalex_id = item.get('id', '')
        paper_id = doi_id if doi_id else openalex_id

        # Concepts / topics as categories
        concepts = item.get('concepts', [])
        categories = [c.get('display_name', '') for c in concepts[:5] if c.get('display_name')]

        # Citation count
        citation_count = item.get('cited_by_count', 0)

        # Journal name from primary location
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
    """
    OpenAlex stores abstracts as an inverted index:
        {"word1": [0, 5], "word2": [1, 3], ...}
    This means "word1" appears at positions 0 and 5, etc.
    We reconstruct the original text by inverting this mapping.
    """
    if not inverted_index:
        return ''

    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return ' '.join(word for _, word in word_positions)


# ---------------------------------------------------------------------------
# Unified Search Function
# ---------------------------------------------------------------------------

def search_papers(query: str, source: str = 'all', max_results: int = 10) -> list[dict]:
    """
    Search for papers across multiple sources.

    Args:
        query: Search terms
        source: 'arxiv', 'semantic_scholar', 'crossref', 'openalex', or 'all'
        max_results: Max results per source

    Returns:
        Combined list of paper dicts.
    """
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
