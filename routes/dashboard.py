from datetime import datetime, timedelta
from flask import Blueprint
from flask_login import login_required, current_user
from sqlalchemy import func
from extensions import db
from models import Bookmark, Collection, SearchHistory, PaperView
from errors import api_success

bp = Blueprint('dashboard', __name__)

@bp.route('/api/dashboard/stats')
@login_required
def stats():
    uid = current_user.id
    total_bookmarks = Bookmark.query.filter_by(user_id=uid).count()
    total_collections = Collection.query.filter_by(user_id=uid).count()
    total_searches = SearchHistory.query.filter_by(user_id=uid).count()
    total_views = PaperView.query.filter_by(user_id=uid).count()

    top_source_row = (
        db.session.query(SearchHistory.source, func.count(SearchHistory.id))
        .filter_by(user_id=uid)
        .group_by(SearchHistory.source)
        .order_by(func.count(SearchHistory.id).desc())
        .first()
    )
    top_source = top_source_row[0] if top_source_row else 'N/A'

    top_queries = (
        db.session.query(
            SearchHistory.search_query, func.count(SearchHistory.id).label('cnt')
        )
        .filter(SearchHistory.user_id == uid)
        .group_by(SearchHistory.search_query)
        .order_by(func.count(SearchHistory.id).desc())
        .limit(5)
        .all()
    )
    topics = [{'query': r[0], 'count': r[1]} for r in top_queries]

    return api_success({
        'total_bookmarks': total_bookmarks,
        'total_collections': total_collections,
        'total_searches': total_searches,
        'total_views': total_views,
        'top_source': top_source,
        'topics': topics,
    })


@bp.route('/api/dashboard/chart')
@login_required
def chart():
    uid = current_user.id
    today = datetime.utcnow().date()
    days = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())

        searches = SearchHistory.query.filter(
            SearchHistory.user_id == uid,
            SearchHistory.searched_at >= day_start,
            SearchHistory.searched_at < day_end,
        ).count()

        views = PaperView.query.filter(
            PaperView.user_id == uid,
            PaperView.viewed_at >= day_start,
            PaperView.viewed_at < day_end,
        ).count()

        days.append({
            'date': day.isoformat(),
            'label': day.strftime('%a'),
            'searches': searches,
            'views': views,
        })

    return api_success({'days': days})


@bp.route('/api/dashboard/activity')
@login_required
def activity():
    uid = current_user.id
    recent_searches = (
        SearchHistory.query
        .filter_by(user_id=uid)
        .order_by(SearchHistory.searched_at.desc())
        .limit(15)
        .all()
    )
    recent_views = (
        PaperView.query
        .filter_by(user_id=uid)
        .order_by(PaperView.viewed_at.desc())
        .limit(15)
        .all()
    )

    return api_success({
        'searches': [s.to_dict() for s in recent_searches],
        'views': [v.to_dict() for v in recent_views],
    })


@bp.route('/api/dashboard/history', methods=['DELETE'])
@login_required
def clear_history():
    SearchHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return api_success(message='Search history cleared.')