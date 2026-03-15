"""
routes/__init__.py — Blueprint registration.

Single function to register all route blueprints on the Flask app.
"""

from routes.auth import bp as auth_bp
from routes.bookmarks import bp as bookmarks_bp
from routes.search import bp as search_bp
from routes.chat import bp as chat_bp
from routes.news import bp as news_bp
from routes.pages import bp as pages_bp
from routes.citations import bp as citations_bp
from routes.collections import bp as collections_bp
from routes.dashboard import bp as dashboard_bp


def register_routes(app):
    """Register all route blueprints on the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(bookmarks_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(citations_bp)
    app.register_blueprint(collections_bp)
    app.register_blueprint(dashboard_bp)
