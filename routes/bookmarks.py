from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from extensions import db
from models import Bookmark
from errors import api_success, api_error, NotFoundError
from validators import require_json, validate_string, validate_int

bp = Blueprint('bookmarks', __name__)

@bp.route('/bookmarks')
@login_required
def page():
    return render_template('bookmarks.html')

@bp.route('/api/bookmarks', methods=['GET'])
@login_required
def get_all():
    page = validate_int(request.args.get('page'), 'page', min_val=1, default=1)
    limit = validate_int(request.args.get('limit'), 'limit', min_val=1, max_val=100, default=20)

    query = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.saved_at.desc())
    total = query.count()
    bookmarks = query.offset((page - 1) * limit).limit(limit).all()

    return api_success(
        [b.to_dict() for b in bookmarks],
        pagination={
            'page': page,
            'limit': limit,
            'total': total,
            'pages': max(1, -(-total // limit)),  # ceil division
        },
    )


@bp.route('/api/bookmarks', methods=['POST'])
@login_required
@require_json('paper_id', 'title')
def add():
    data = request.get_json()
    paper_id = validate_string(data['paper_id'], 'paper_id', max_len=256)
    title = validate_string(data['title'], 'title', max_len=512)

    existing = Bookmark.query.filter_by(
        user_id=current_user.id, paper_id=paper_id
    ).first()
    if existing:
        return api_success(
            existing.to_dict(),
            message='Already bookmarked.',
        )

    bookmark = Bookmark(
        user_id=current_user.id,
        paper_id=paper_id,
        title=title,
        authors=data.get('authors', ''),
        summary=data.get('summary', ''),
        pdf_url=data.get('pdf_url', ''),
        source=data.get('source', 'arxiv'),
    )
    db.session.add(bookmark)
    db.session.commit()

    return api_success(
        bookmark.to_dict(),
        message='Bookmarked successfully.',
        status=201,
    )


@bp.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def remove(bookmark_id):
    bookmark = Bookmark.query.filter_by(
        id=bookmark_id, user_id=current_user.id
    ).first()
    if not bookmark:
        raise NotFoundError('Bookmark not found.')
    db.session.delete(bookmark)
    db.session.commit()
    return api_success(message='Bookmark removed.')


@bp.route('/api/bookmarks/check/<path:paper_id>')
@login_required
def check(paper_id):
    bookmark = Bookmark.query.filter_by(
        user_id=current_user.id, paper_id=paper_id
    ).first()
    return api_success({
        'bookmarked': bookmark is not None,
        'bookmark_id': bookmark.id if bookmark else None,
    })
