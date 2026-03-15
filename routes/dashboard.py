"""
routes/dashboard.py — Dashboard API routes.

Provides stats and activity data for the user dashboard.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import Bookmark, Collection, SearchHistory, PaperView

bp = Blueprint('dashboard', __name__)


@bp.route('/api/dashboard/stats')
@login_required
def stats():
    """Return aggregated stats for the current user's dashboard."""
    uid = current_user.id
    total_bookmarks = Bookmark.query.filter_by(user_id=uid).count()
    total_collections = Collection.query.filter_by(user_id=uid).count()
    total_searches = SearchHistory.query.filter_by(user_id=uid).count()
    total_views = PaperView.query.filter_by(user_id=uid).count()

    # Most-used search source
    top_source_row = db.session.query(
        SearchHistory.source, func.count(SearchHistory.id)
    ).filter_by(user_id=uid).group_by(SearchHistory.source)\
     .order_by(func.count(SearchHistory.id).desc()).first()
    top_source = top_source_row[0] if top_source_row else 'N/A'

    return jsonify({
        'total_bookmarks': total_bookmarks,
        'total_collections': total_collections,
        'total_searches': total_searches,
        'total_views': total_views,
        'top_source': top_source,
    })


@bp.route('/api/dashboard/activity')
@login_required
def activity():
    """Return recent searches and recently viewed papers."""
    uid = current_user.id
    recent_searches = SearchHistory.query.filter_by(user_id=uid)\
        .order_by(SearchHistory.searched_at.desc()).limit(15).all()
    recent_views = PaperView.query.filter_by(user_id=uid)\
        .order_by(PaperView.viewed_at.desc()).limit(15).all()

    return jsonify({
        'searches': [s.to_dict() for s in recent_searches],
        'views': [v.to_dict() for v in recent_views],
    })


@bp.route('/api/dashboard/history', methods=['DELETE'])
@login_required
def clear_history():
    """Clear all search history for the current user."""
    SearchHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'message': 'Search history cleared.'})
