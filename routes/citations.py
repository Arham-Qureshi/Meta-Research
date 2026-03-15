"""
routes/citations.py — Citation export API routes.

Provides endpoints for formatting individual paper citations
and bulk-exporting bookmarks as BibTeX.
"""

from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from models import Bookmark
from services.citations import format_citation, bulk_bibtex, FORMAT_MAP

bp = Blueprint('citations', __name__)


@bp.route('/api/cite', methods=['POST'])
def cite_paper():
    """Return a formatted citation string for a single paper."""
    data = request.get_json()
    if not data or not data.get('paper'):
        return jsonify({'error': 'paper object is required.'}), 400

    fmt = data.get('format', 'bibtex')
    if fmt not in FORMAT_MAP:
        return jsonify({'error': f'Unknown format. Supported: {", ".join(FORMAT_MAP)}'}), 400

    citation = format_citation(data['paper'], fmt)
    return jsonify({'citation': citation, 'format': fmt})


@bp.route('/api/bookmarks/export')
@login_required
def export_bookmarks():
    """Export all user bookmarks as a downloadable .bib file."""
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id)\
                              .order_by(Bookmark.saved_at.desc()).all()
    if not bookmarks:
        return jsonify({'error': 'No bookmarks to export.'}), 404

    papers = [b.to_dict() for b in bookmarks]
    bib_content = bulk_bibtex(papers)

    return Response(
        bib_content,
        mimetype='application/x-bibtex',
        headers={'Content-Disposition': 'attachment; filename=meta_research_bookmarks.bib'},
    )
