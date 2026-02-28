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
# Unified Search Function
# ---------------------------------------------------------------------------

def search_papers(query: str, source: str = 'all', max_results: int = 10) -> list[dict]:
    """
    Search for papers across multiple sources.

    Args:
        query: Search terms
        source: 'arxiv', 'semantic_scholar', or 'all'
        max_results: Max results per source

    Returns:
        Combined list of paper dicts.
    """
    results = []

    if source in ('arxiv', 'all'):
        results.extend(search_arxiv(query, max_results))

    if source in ('semantic_scholar', 'all'):
        # Small delay to be respectful of rate limits
        if source == 'all':
            time.sleep(0.5)
        results.extend(search_semantic_scholar(query, max_results))

    return results
