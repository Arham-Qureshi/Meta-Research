from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('pages', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/discover')
def discover():
    return render_template('discover.html')

@bp.route('/paper/<path:paper_id>')
def paper_chat(paper_id):
    if current_user.is_authenticated:
        from extensions import db
        from models import PaperView
        view = PaperView(
            user_id=current_user.id,
            paper_id=paper_id,
            title=paper_id,
        )
        db.session.add(view)
        db.session.commit()
    return render_template('paper_chat.html', paper_id=paper_id)

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
