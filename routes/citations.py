from flask import Blueprint, request, Response
from flask_login import login_required, current_user
from models import Bookmark
from services.citations import format_citation, bulk_bibtex, FORMAT_MAP
from errors import api_success, ValidationError, NotFoundError
from validators import require_json

bp = Blueprint('citations', __name__)

@bp.route('/api/cite', methods=['POST'])
@require_json('paper')
def cite_paper():
    data = request.get_json()

    paper = data['paper']
    if not isinstance(paper, dict):
        raise ValidationError('paper must be a JSON object.')

    fmt = data.get('format', 'bibtex')
    if fmt not in FORMAT_MAP:
        raise ValidationError(
            f'Unknown format "{fmt}". Supported: {", ".join(FORMAT_MAP)}',
        )

    citation = format_citation(paper, fmt)
    return api_success({
        'citation': citation,
        'format': fmt,
    })

@bp.route('/api/bookmarks/export')
@login_required
def export_bookmarks():
    bookmarks = (
        Bookmark.query
        .filter_by(user_id=current_user.id)
        .order_by(Bookmark.saved_at.desc())
        .all()
    )
    if not bookmarks:
        raise NotFoundError('No bookmarks to export.')

    papers = [b.to_dict() for b in bookmarks]
    bib_content = bulk_bibtex(papers)

    return Response(
        bib_content,
        mimetype='application/x-bibtex',
        headers={'Content-Disposition': 'attachment; filename=meta_research_bookmarks.bib'},
    )
