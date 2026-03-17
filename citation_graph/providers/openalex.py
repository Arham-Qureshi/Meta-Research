from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

API_BASE = "https://api.openalex.org/works"
_MAILTO = "metaresearch@example.com"

_NODE_FIELDS = "id,doi,title,authorships,publication_date,cited_by_count,abstract_inverted_index,concepts"
_CENTER_FIELDS = (
    "id,doi,title,authorships,publication_date,cited_by_count,"
    "referenced_works,cited_by_api_url,abstract_inverted_index,concepts,related_works"
)

def resolve_id(paper_id: str) -> str:
    pid = paper_id.strip()

    if pid.startswith("https://openalex.org/"):
        return pid

    if pid.startswith("10.") or pid.startswith("doi:"):
        doi = pid.removeprefix("doi:")
        return f"https://doi.org/{doi}"

    if pid.startswith("https://doi.org/"):
        return pid

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

def _extract_concepts(concepts: list[dict] | None, limit: int = 5) -> list[str]:
    """Extract top concept display names from OpenAlex concept objects."""
    if not concepts:
        return []
    sorted_c = sorted(concepts, key=lambda c: c.get("score", 0), reverse=True)
    return [c.get("display_name", "") for c in sorted_c[:limit] if c.get("display_name")]

def _make_node(item: dict, node_type: str) -> dict:
    """Build a standardised node dict from a raw OpenAlex work object."""
    return {
        "id": item.get("id", ""),
        "label": item.get("title", "Untitled"),
        "year": _year_from_date(item.get("publication_date")),
        "citations": item.get("cited_by_count", 0),
        "type": node_type,
        "authors": _authors_str(item.get("authorships", []), 2),
        "doi": _clean_doi(item.get("doi")),
        "summary": _reconstruct_abstract(item.get("abstract_inverted_index")),
        "concepts": _extract_concepts(item.get("concepts")),
    }

def _fetch_batch(ids: list[str], max_items: int,
                 node_type: str) -> list[tuple[dict, dict]]:
    if not ids:
        return []

    oa_filter = "|".join(ids[:max_items])
    try:
        resp = requests.get(
            API_BASE,
            params={
                "filter": f"openalex:{oa_filter}",
                "select": _NODE_FIELDS,
                "per_page": max_items,
                "mailto": _MAILTO,
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("results", [])
    except Exception as exc:
        print(f"[OpenAlex] _fetch_batch({node_type}) error: {exc}")
        return []

    results = []
    for item in items:
        node = _make_node(item, node_type)
        results.append((node, {"peer_id": node["id"]}))
    return results

def _fetch_citing(cited_by_url: str, max_items: int) -> list[tuple[dict, dict]]:
    if not cited_by_url:
        return []
    try:
        resp = requests.get(
            cited_by_url,
            params={
                "select": _NODE_FIELDS,
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
        node = _make_node(item, "citation")
        results.append((node, {"peer_id": node["id"]}))
    return results

def _fetch_related(related_ids: list[str], max_items: int) -> list[tuple[dict, dict]]:
    if not related_ids:
        return []
    return _fetch_batch(related_ids, max_items, "related")

def fetch_graph(paper_id: str, max_citations: int = 20,
                max_references: int = 20,
                fallback_doi: str = "",
                fallback_title: str = "") -> dict:
    oa_id = resolve_id(paper_id)

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

    try:
        resp = requests.get(
            f"{API_BASE}/{oa_id}",
            params={"select": _CENTER_FIELDS, "mailto": _MAILTO},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _error_response("OpenAlex API failed")

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
        "concepts": _extract_concepts(data.get("concepts")),
    }

    nodes = [{
        "id": center_id, "label": center["title"], "year": year,
        "citations": center["citationCount"], "type": "center",
        "authors": center["authors"], "doi": doi,
        "summary": center["summary"],
        "concepts": center["concepts"],
    }]
    edges = []
    seen = {center_id}

    ref_ids = data.get("referenced_works", [])[:max_references]
    cited_by_url = data.get("cited_by_api_url", "")
    related_ids = data.get("related_works", [])[:10]

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_fetch_batch, ref_ids, max_references, "reference"): "ref",
            pool.submit(_fetch_citing, cited_by_url, max_citations): "cite",
            pool.submit(_fetch_related, related_ids, 10): "related",
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
                elif kind == "cite":
                    edges.append({"source": nid, "target": center_id})
                else:
                    edges.append({"source": center_id, "target": nid})

    return {
        "center": center, "nodes": nodes, "edges": edges,
        "source": "openalex", "error": None,
    }

def _error_response(msg: str) -> dict:
    return {"center": None, "nodes": [], "edges": [],
            "source": "openalex", "error": msg}
