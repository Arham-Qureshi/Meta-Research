"""
routes.py — Flask Blueprint routes for the Citation Graph feature.

Endpoints:
    GET  /citation-graph           → standalone page
    GET  /api/paper/graph          → JSON citation network
"""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
import json

bp = Blueprint(
    "citation_graph",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/citation_graph/static",
)

@bp.route("/citation-graph")
def page():
    return render_template("citation_graph.html")

@bp.route("/api/paper/graph", methods=["GET"])
def api_graph():
    from citation_graph.graph_builder import build_graph

    paper_id = request.args.get("id", "").strip()
    if not paper_id:
        return jsonify({"error": 'Paper ID parameter "id" is required.'}), 400

    source = request.args.get("source", "semantic_scholar").strip()
    if source not in ("semantic_scholar", "openalex"):
        source = "semantic_scholar"

    max_cite = request.args.get("max_citations", 15, type=int)
    max_ref = request.args.get("max_references", 15, type=int)

    from extensions import db
    from models import GraphCache

    cache_entry = GraphCache.query.filter_by(
        paper_id=paper_id, source=source
    ).first()

    if cache_entry and (datetime.utcnow() - cache_entry.created_at) < timedelta(days=7):
        return jsonify(json.loads(cache_entry.graph_json))

    result = build_graph(
        paper_id,
        source=source,
        max_citations=max_cite,
        max_references=max_ref,
    )

    if result.get("error"):
        return jsonify({"error": result["error"]}), 502

    actual_source = result.get("source", source)
    try:
        if cache_entry:
            cache_entry.graph_json = json.dumps(result)
            cache_entry.created_at = datetime.utcnow()
        else:
            cache_entry = GraphCache(
                paper_id=paper_id,
                source=actual_source,
                graph_json=json.dumps(result),
            )
            db.session.add(cache_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify(result)
