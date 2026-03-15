"""
routes/search.py — Paper search API route.

Delegates to SearchService which composes the provider registry.
Tracks searches in SearchHistory for logged-in users.
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user
from services.search import search_service

bp = Blueprint('search', __name__)


@bp.route('/api/search')
def api_search():
    """Search for research papers across registered providers."""
    query = request.args.get('q', '').strip()
    source = request.args.get('source', 'arxiv')
    max_results = request.args.get('max', 10, type=int)

    if not query:
        return jsonify({'error': 'Query parameter "q" is required.'}), 400

    results = search_service.search(query, source=source, max_results=max_results)

    # Track search for logged-in users
    if current_user.is_authenticated:
        from extensions import db
        from models import SearchHistory
        entry = SearchHistory(
            user_id=current_user.id,
            search_query=query,
            source=source,
            result_count=len(results),
        )
        db.session.add(entry)
        db.session.commit()

    return jsonify({
        'query': query,
        'source': source,
        'count': len(results),
        'papers': results,
    })
