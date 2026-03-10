"""
OpenAlex citation graph provider.

Fetches paper metadata, citations, and references from the OpenAlex API
and returns a normalised graph dict.  Uses ThreadPoolExecutor for parallel
fetching of references and citing papers.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ── Constants ────────────────────────────────────────────────────
API_BASE = "https://api.openalex.org/works"
_MAILTO = "metaresearch@example.com"


# ── ID Resolution ────────────────────────────────────────────────
def resolve_id(paper_id: str) -> str:
    """
    Normalise a paper identifier for the OpenAlex API.

    Accepted:
        - DOI          → https://doi.org/10.xxxx/…
        - OpenAlex URL → pass through
        - S.S. hex ID  → unsupported (returns empty)
    """
    pid = paper_id.strip()

    if pid.startswith("https://openalex.org/"):
        return pid

    if pid.startswith("10.") or pid.startswith("doi:"):
        doi = pid.removeprefix("doi:")
        return f"https://doi.org/{doi}"

    if pid.startswith("https://doi.org/"):
        return pid

    # 40-hex S.S. hash — OpenAlex can't resolve directly
    if len(pid) == 40 and all(c in "0123456789abcdef" for c in pid.lower()):
        return ""

    return pid


def search_by_title(title: str) -> str:
    """Search OpenAlex by title.  Returns the first matching OpenAlex ID or ''."""
    try:
        resp = requests.get(
            API_BASE,
            params={"search": title, "select": "id", "per_page": 1,
                    "mailto": _MAILTO},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0].get("id", "") if results else ""
    except Exception:
        return ""


# ── Helpers ──────────────────────────────────────────────────────
def _authors_str(authorships: list[dict], limit: int = 3) -> str:
    return ", ".join(
        a.get("author", {}).get("display_name", "")
        for a in (authorships or [])[:limit]
    )


def _clean_doi(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.replace("https://doi.org/", "")


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str or len(date_str) < 4:
        return None
    y = date_str[:4]
    return int(y) if y.isdigit() else None


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


# ── Batch Fetcher (reusable) ────────────────────────────────────
def _fetch_batch(ids: list[str], max_items: int,
                 node_type: str) -> list[tuple[dict, dict]]:
    """
    Fetch a batch of OpenAlex works by ID.

    Returns list of (node_dict, edge_fragment) tuples.
    edge_fragment has { 'peer_id': str } so the caller can wire edges.
    """
    if not ids:
        return []

    oa_filter = "|".join(ids[:max_items])
    try:
        resp = requests.get(
            API_BASE,
            params={
                "filter": f"openalex:{oa_filter}",
                "select": "id,doi,title,authorships,publication_date,cited_by_count",
                "per_page": max_items,
                "mailto": _MAILTO,
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("results", [])
    except Exception:
        return []

    results = []
    for item in items:
        nid = item.get("id", "")
        results.append(({
            "id": nid,
            "label": item.get("title", "Untitled"),
            "year": _year_from_date(item.get("publication_date")),
            "citations": item.get("cited_by_count", 0),
            "type": node_type,
            "authors": _authors_str(item.get("authorships", []), 2),
            "doi": _clean_doi(item.get("doi")),
        }, {"peer_id": nid}))
    return results


def _fetch_citing(cited_by_url: str, max_items: int) -> list[tuple[dict, dict]]:
    """Fetch papers that cite this paper using the cited_by_api_url."""
    if not cited_by_url:
        return []
    try:
        resp = requests.get(
            cited_by_url,
            params={
                "select": "id,doi,title,authorships,publication_date,cited_by_count",
                "per_page": max_items,
                "mailto": _MAILTO,
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("results", [])
    except Exception:
        return []

    results = []
    for item in items:
        nid = item.get("id", "")
        results.append(({
            "id": nid,
            "label": item.get("title", "Untitled"),
            "year": _year_from_date(item.get("publication_date")),
            "citations": item.get("cited_by_count", 0),
            "type": "citation",
            "authors": _authors_str(item.get("authorships", []), 2),
            "doi": _clean_doi(item.get("doi")),
        }, {"peer_id": nid}))
    return results


# ── Public API ───────────────────────────────────────────────────
def fetch_graph(paper_id: str, max_citations: int = 20,
                max_references: int = 20,
                fallback_doi: str = "",
                fallback_title: str = "") -> dict:
    """
    Build a citation graph dict from OpenAlex.

    Uses ThreadPoolExecutor to fetch references and citations in parallel.
    """
    oa_id = resolve_id(paper_id)

    # If raw S.S. hex ID that couldn't resolve, try fallback DOI / title
    if not oa_id:
        if fallback_doi:
            oa_id = f"https://doi.org/{fallback_doi}"
        elif fallback_title:
            oa_id = search_by_title(fallback_title)
        if not oa_id:
            return _error_response(
                "Cannot resolve this paper ID for OpenAlex. "
                "Try searching with a DOI or use Semantic Scholar."
            )

    # ── Fetch center paper ───────────────────────────────────────
    fields = ("id,doi,title,authorships,publication_date,cited_by_count,"
              "referenced_works,cited_by_api_url,abstract_inverted_index")
    try:
        resp = requests.get(
            f"{API_BASE}/{oa_id}",
            params={"select": fields, "mailto": _MAILTO},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _error_response("OpenAlex API failed")

    # Center node
    center_id = data.get("id", "")
    doi = _clean_doi(data.get("doi"))
    year = _year_from_date(data.get("publication_date"))
    center = {
        "id": center_id,
        "title": data.get("title", "Unknown"),
        "authors": _authors_str(data.get("authorships", [])),
        "year": year,
        "citationCount": data.get("cited_by_count", 0),
        "doi": doi,
        "summary": _reconstruct_abstract(data.get("abstract_inverted_index")),
    }

    nodes = [{
        "id": center_id, "label": center["title"], "year": year,
        "citations": center["citationCount"], "type": "center",
        "authors": center["authors"], "doi": doi,
    }]
    edges = []
    seen = {center_id}

    # ── Parallel fetch: references + citations ───────────────────
    ref_ids = data.get("referenced_works", [])[:max_references]
    cited_by_url = data.get("cited_by_api_url", "")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_fetch_batch, ref_ids, max_references, "reference"): "ref",
            pool.submit(_fetch_citing, cited_by_url, max_citations): "cite",
        }
        for future in as_completed(futures):
            kind = futures[future]
            try:
                items = future.result()
            except Exception:
                continue
            for node, meta in items:
                nid = node["id"]
                if nid in seen:
                    continue
                seen.add(nid)
                nodes.append(node)
                if kind == "ref":
                    edges.append({"source": center_id, "target": nid})
                else:
                    edges.append({"source": nid, "target": center_id})

    return {
        "center": center, "nodes": nodes, "edges": edges,
        "source": "openalex", "error": None,
    }


def _error_response(msg: str) -> dict:
    return {"center": None, "nodes": [], "edges": [],
            "source": "openalex", "error": msg}
