"""
citation_graph — self-contained Flask Blueprint for citation network graphs.

Usage in app.py:
    from citation_graph import create_blueprint
    app.register_blueprint(create_blueprint())
"""

from citation_graph.routes import bp


def create_blueprint():
    """Return the configured Citation Graph blueprint."""
    return bp
