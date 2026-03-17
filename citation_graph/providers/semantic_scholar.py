import re
import time
import requests

API_BASE = "https://api.semanticscholar.org/graph/v1/paper"
_MIN_INTERVAL = 1.5
_last_request_ts: float = 0

def _rate_limit() -> None:
    global _last_request_ts
    wait = _MIN_INTERVAL - (time.time() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.time()

def resolve_id(paper_id: str) -> str:
    pid = paper_id.strip()

    if len(pid) == 40 and all(c in "0123456789abcdef" for c in pid.lower()):
        return pid

    if pid.startswith("10.") or pid.startswith("doi:"):
        return f"DOI:{pid.removeprefix('doi:')}"

    m = re.match(r"^(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)$", pid)
    if m:
        return f"ArXiv:{m.group(1)}"

    return pid

def _extract_doi(ext_ids: dict | None) -> str:
    if not ext_ids:
        return ""
    return ext_ids.get("DOI", "") or ""

def _authors_str(authors: list[dict], limit: int = 3) -> str:
    return ", ".join(a.get("name", "") for a in (authors or [])[:limit])

def _extract_concepts(fields: list[dict] | None, limit: int = 5) -> list[str]:
    if not fields:
        return []
    return [f.get("category", "") for f in fields[:limit] if f.get("category")]

def _make_node(item: dict, node_type: str) -> dict:
    return {
        "id": item.get("paperId", ""),
        "label": item.get("title", "Untitled"),
        "year": item.get("year"),
        "citations": item.get("citationCount", 0),
        "type": node_type,
        "authors": _authors_str(item.get("authors", []), 2),
        "doi": _extract_doi(item.get("externalIds")),
        "summary": item.get("abstract", "") or "",
        "concepts": _extract_concepts(item.get("s2FieldsOfStudy")),
    }

def fetch_graph(paper_id: str, max_citations: int = 20,
                max_references: int = 20) -> dict:
    resolved = resolve_id(paper_id)
    fields = (
        "title,authors,year,citationCount,externalIds,abstract,s2FieldsOfStudy,"
        "citations.title,citations.authors,citations.year,"
        "citations.citationCount,citations.externalIds,citations.abstract,citations.s2FieldsOfStudy,"
        "references.title,references.authors,references.year,"
        "references.citationCount,references.externalIds,references.abstract,references.s2FieldsOfStudy"
    )

    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/{resolved}",
            params={"fields": fields, "limit": max(max_citations, max_references)},
            headers={"User-Agent": "MetaResearch/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {
            "center": _fetch_basic_info(resolved),
            "nodes": [], "edges": [],
            "source": "semantic_scholar",
            "error": f"Semantic Scholar API error: {exc}",
        }
    except ValueError:
        return _error_response("Invalid JSON from Semantic Scholar")

    return _build_graph(data, paper_id, max_citations, max_references)

def _fetch_basic_info(resolved_id: str) -> dict | None:
    """Lightweight call for center-paper metadata (works even under rate limit)."""
    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/{resolved_id}",
            params={"fields": "title,externalIds,year,citationCount,authors"},
            headers={"User-Agent": "MetaResearch/1.0"},
            timeout=10,
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "id": d.get("paperId", ""),
                "title": d.get("title", "Unknown"),
                "authors": _authors_str(d.get("authors", [])),
                "year": d.get("year"),
                "citationCount": d.get("citationCount", 0),
                "doi": _extract_doi(d.get("externalIds")),
            }
    except Exception:
        pass
    return None

def _build_graph(data: dict, paper_id: str,
                 max_citations: int, max_references: int) -> dict:
    center_id = data.get("paperId", paper_id)
    center_doi = _extract_doi(data.get("externalIds"))
    center = {
        "id": center_id,
        "title": data.get("title", "Unknown"),
        "authors": _authors_str(data.get("authors", [])),
        "year": data.get("year"),
        "citationCount": data.get("citationCount", 0),
        "doi": center_doi,
        "summary": data.get("abstract", "") or "",
        "concepts": _extract_concepts(data.get("s2FieldsOfStudy")),
    }

    nodes = [{
        "id": center_id,
        "label": center["title"],
        "year": center["year"],
        "citations": center["citationCount"],
        "type": "center",
        "authors": center["authors"],
        "doi": center_doi,
        "summary": center["summary"],
        "concepts": center["concepts"],
    }]
    edges = []
    seen = {center_id}

    for c in (data.get("citations") or [])[:max_citations]:
        cid = c.get("paperId")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        nodes.append(_make_node(c, "citation"))
        edges.append({"source": cid, "target": center_id})

    for r in (data.get("references") or [])[:max_references]:
        rid = r.get("paperId")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        nodes.append(_make_node(r, "reference"))
        edges.append({"source": center_id, "target": rid})

    return {
        "center": center, "nodes": nodes, "edges": edges,
        "source": "semantic_scholar", "error": None,
    }

def _error_response(msg: str) -> dict:
    return {"center": None, "nodes": [], "edges": [],
            "source": "semantic_scholar", "error": msg}
