from flask import Blueprint, request
from extensions import limiter
from services.chat import chat_service
from errors import api_success, api_error, ValidationError
from validators import require_json, validate_string

bp = Blueprint('chat', __name__)

@bp.route('/api/chat', methods=['POST'])
@limiter.limit('15 per minute')
@require_json('paper', 'message')
def api_chat():
    data = request.get_json()

    paper = data['paper']
    if not isinstance(paper, dict) or not paper.get('title'):
        raise ValidationError('Paper object must include a "title" field.')

    message = validate_string(data['message'], 'message', min_len=1, max_len=2000)

    result = chat_service.chat(paper, message)
    if result.get('error'):
        return api_error(result['error'], 500)

    return api_success({'reply': result['reply']})


@bp.route('/api/chat/summarize', methods=['POST'])
@limiter.limit('10 per minute')
@require_json('paper')
def api_summarize():
    data = request.get_json()

    paper = data['paper']
    if not isinstance(paper, dict) or not paper.get('title'):
        raise ValidationError('Paper object must include a "title" field.')

    result = chat_service.summarize(paper)
    if result.get('error'):
        return api_error(result['error'], 500)

    return api_success({'summary': result['summary']})
