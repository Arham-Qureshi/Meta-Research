"""
routes/bookmarks.py — Bookmark CRUD routes.

Uses Bookmark.to_dict() for serialisation (defined once in models.py).
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Bookmark

bp = Blueprint('bookmarks', __name__)


@bp.route('/bookmarks')
@login_required
def page():
    return render_template('bookmarks.html')


@bp.route('/api/bookmarks', methods=['GET'])
@login_required
def get_all():
    """Get all bookmarks for the current user."""
    bmarks = Bookmark.query.filter_by(user_id=current_user.id)\
                           .order_by(Bookmark.saved_at.desc()).all()
    return jsonify({'bookmarks': [b.to_dict() for b in bmarks]})


@bp.route('/api/bookmarks', methods=['POST'])
@login_required
def add():
    """Add a bookmark for the current user."""
    data = request.get_json()
    if not data or not data.get('paper_id') or not data.get('title'):
        return jsonify({'error': 'paper_id and title are required.'}), 400

    existing = Bookmark.query.filter_by(
        user_id=current_user.id, paper_id=data['paper_id']
    ).first()
    if existing:
        return jsonify({'message': 'Already bookmarked.'}), 200

    bookmark = Bookmark(
        user_id=current_user.id,
        paper_id=data['paper_id'],
        title=data['title'],
        authors=data.get('authors', ''),
        summary=data.get('summary', ''),
        pdf_url=data.get('pdf_url', ''),
        source=data.get('source', 'arxiv'),
    )
    db.session.add(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmarked successfully.', 'id': bookmark.id}), 201


@bp.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def remove(bookmark_id):
    """Remove a bookmark for the current user."""
    bookmark = Bookmark.query.filter_by(
        id=bookmark_id, user_id=current_user.id
    ).first()
    if not bookmark:
        return jsonify({'error': 'Bookmark not found.'}), 404
    db.session.delete(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmark removed.'})


@bp.route('/api/bookmarks/check/<path:paper_id>')
@login_required
def check(paper_id):
    """Check if a paper is bookmarked by the current user."""
    bookmark = Bookmark.query.filter_by(
        user_id=current_user.id, paper_id=paper_id
    ).first()
    return jsonify({
        'bookmarked': bookmark is not None,
        'bookmark_id': bookmark.id if bookmark else None,
    })
