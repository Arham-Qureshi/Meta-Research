from flask import Blueprint, request, jsonify
from flask_login import current_user
from services.search import search_service

bp = Blueprint('search', __name__)

@bp.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    source = request.args.get('source', 'arxiv')
    max_results = request.args.get('max', 10, type=int)

    if not query:
        return jsonify({'error': 'Query parameter "q" is required.'}), 400

    results = search_service.search(query, source=source, max_results=max_results)

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

from concurrent.futures import ThreadPoolExecutor

@bp.route('/api/suggest')
def api_suggest():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return jsonify([])
    
    from services.providers import get_all_providers
    providers = get_all_providers()
    suggestions = []
    
    def fetch_provider(provider):
        try:
            results = provider.search(query, max_results=1)
            if results:
                paper = results[0]
                hint_str = paper.get('source_name', paper.get('source', 'Unknown'))
                authors = paper.get('authors', '')
                if authors and authors != 'Unknown authors':
                    authors_split = authors.split(',')
                    short_authors = authors_split[0] + (' et al.' if len(authors_split) > 1 else '')
                    hint_str += f" · {short_authors}"
                
                return {
                    'id': paper.get('id', ''),
                    'title': paper.get('title', ''),
                    'hint': hint_str,
                    'source': paper.get('source', '')
                }
        except Exception as e:
            print(f"Error fetching suggestion from {provider}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=max(1, len(providers))) as executor:
        futures = [executor.submit(fetch_provider, p) for p in providers]
        for future in futures:
            try:
                res = future.result(timeout=1.5)
                if res:
                    suggestions.append(res)
            except Exception as e:
                print(f"Provider timed out or failed: {e}")
                
    return jsonify(suggestions)
