from flask import Blueprint, request
from services.news import news_service
from errors import api_success
from validators import validate_int

bp = Blueprint('news', __name__)

@bp.route('/api/news')
def api_news():
    query = request.args.get('q', None)
    articles = news_service.get_news(query=query)
    return api_success(
        articles,
        count=len(articles),
    )


@bp.route('/api/trending')
def api_trending():
    max_results = validate_int(
        request.args.get('max'), 'max', min_val=1, max_val=25, default=12
    )
    papers = news_service.get_trending(max_results=max_results)
    return api_success(
        papers,
        count=len(papers),
    )
