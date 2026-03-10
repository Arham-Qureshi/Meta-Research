"""
routes/chat.py — AI chat and summarisation routes.

Delegates to ChatService.
"""

from flask import Blueprint, request, jsonify
from services.chat import chat_service

bp = Blueprint('chat', __name__)


@bp.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat with a paper using AI."""
    data = request.get_json()
    if not data or not data.get('paper') or not data.get('message'):
        return jsonify({'error': 'paper and message are required.'}), 400

    result = chat_service.chat(data['paper'], data['message'])
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    return jsonify({'reply': result['reply']})


@bp.route('/api/chat/summarize', methods=['POST'])
def api_summarize():
    """Generate a comprehensive summary of a paper."""
    data = request.get_json()
    if not data or not data.get('paper'):
        return jsonify({'error': 'paper data is required.'}), 400

    result = chat_service.summarize(data['paper'])
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    return jsonify({'summary': result['summary']})
