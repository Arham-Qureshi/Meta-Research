from flask import Blueprint, request
from flask_login import current_user
from extensions import limiter
from services.search import search_service
from errors import api_success, ValidationError
from validators import validate_string, validate_int

bp = Blueprint('search', __name__)

@bp.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        raise ValidationError('Query parameter "q" is required.')

    source = request.args.get('source', 'arxiv')
    max_results = validate_int(
        request.args.get('max'), 'max', min_val=1, max_val=50, default=10
    )

    results = search_service.search(query, source=source, max_results=max_results)

    # Track search history 
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

    return api_success(
        results,
        query=query,
        source=source,
        count=len(results),
    )


@bp.route('/api/suggest')
@limiter.limit('30 per minute')
def api_suggest():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return api_success([])

    from concurrent.futures import ThreadPoolExecutor
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
                    'source': paper.get('source', ''),
                }
        except Exception as e:
            print(f"Error fetching suggestion from {provider}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=max(1, len(list(providers)))) as executor:
        from services.providers import get_all_providers as gap
        all_providers = list(gap())
        futures = [executor.submit(fetch_provider, p) for p in all_providers]
        for future in futures:
            try:
                res = future.result(timeout=1.5)
                if res:
                    suggestions.append(res)
            except Exception as e:
                print(f"Provider timed out or failed: {e}")

    return api_success(suggestions)