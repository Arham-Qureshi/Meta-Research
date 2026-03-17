from flask import Blueprint, request, jsonify
from services.news import news_service

bp = Blueprint('news', __name__)

@bp.route('/api/news')
def api_news():
    query = request.args.get('q', None)
    articles = news_service.get_news(query=query)
    return jsonify({'count': len(articles), 'articles': articles})

@bp.route('/api/trending')
def api_trending():
    max_results = request.args.get('max', 12, type=int)
    papers = news_service.get_trending(max_results=max_results)
    return jsonify({'count': len(papers), 'papers': papers})
