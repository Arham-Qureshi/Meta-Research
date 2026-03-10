"""
routes/pages.py — Page-render routes (no API logic, just renders).
"""

from flask import Blueprint, render_template

bp = Blueprint('pages', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/discover')
def discover():
    """Discover page — trending papers & science news."""
    return render_template('discover.html')


@bp.route('/paper/<path:paper_id>')
def paper_chat(paper_id):
    """Paper detail + chat page."""
    return render_template('paper_chat.html', paper_id=paper_id)
