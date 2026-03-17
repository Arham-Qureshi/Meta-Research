from citation_graph.providers import semantic_scholar as ss_provider
from citation_graph.providers import openalex as oa_provider

def build_graph(paper_id: str, *,
                source: str = "semantic_scholar",
                max_citations: int = 20,
                max_references: int = 20) -> dict:
    source = source if source in ("semantic_scholar", "openalex") else "semantic_scholar"

    primary_fn, fallback_fn = _provider_pair(source)

    result = primary_fn(paper_id, max_citations, max_references)

    if _is_usable(result):
        result["fallback_used"] = False
        return result

    fallback_hints = _extract_hints(result, paper_id)
    fallback_result = fallback_fn(
        paper_id, max_citations, max_references, **fallback_hints
    )

    if _is_usable(fallback_result):
        fallback_result["fallback_used"] = True
        return fallback_result

    return {
        "center": result.get("center") or fallback_result.get("center"),
        "nodes": [], "edges": [],
        "source": source,
        "fallback_used": True,
        "error": (
            f"Primary ({source}) failed: {result.get('error', 'unknown')}. "
            f"Fallback also failed: {fallback_result.get('error', 'unknown')}."
        ),
    }

def _provider_pair(source: str):
    if source == "openalex":
        return _oa_fetch, _ss_fetch
    return _ss_fetch, _oa_fetch

def _ss_fetch(paper_id, max_c, max_r, **_kwargs):
    return ss_provider.fetch_graph(paper_id, max_c, max_r)

def _oa_fetch(paper_id, max_c, max_r, **kwargs):
    return oa_provider.fetch_graph(
        paper_id, max_c, max_r,
        fallback_doi=kwargs.get("fallback_doi", ""),
        fallback_title=kwargs.get("fallback_title", ""),
    )

def _is_usable(result: dict) -> bool:
    return (
        result.get("error") is None
        and len(result.get("nodes", [])) > 1
        and len(result.get("edges", [])) > 0
    )

def _extract_hints(result: dict, paper_id: str) -> dict:
    hints: dict[str, str] = {}
    center = result.get("center")
    if center:
        if center.get("doi"):
            hints["fallback_doi"] = center["doi"]
        if center.get("title") and center["title"] != "Unknown":
            hints["fallback_title"] = center["title"]
    return hints
