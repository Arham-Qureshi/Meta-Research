"""
Meta Research - Research Paper Discovery Service
Main Flask Application
"""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'meta_research.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.String(256), nullable=False)      # ArXiv ID or unique key
    title = db.Column(db.String(512), nullable=False)
    authors = db.Column(db.String(512))
    summary = db.Column(db.Text)
    pdf_url = db.Column(db.String(512))
    source = db.Column(db.String(64))                          # e.g. "arxiv"
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Prevent duplicate bookmarks per user
    __table_args__ = (db.UniqueConstraint('user_id', 'paper_id', name='uq_user_paper'),)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')

        # Validation
        if not username or not email or not password:
            msg = 'All fields are required.'
            return (jsonify({'error': msg}), 400) if request.is_json else (flash(msg, 'error'), redirect(url_for('signup')))[1]

        if User.query.filter((User.username == username) | (User.email == email)).first():
            msg = 'Username or email already exists.'
            return (jsonify({'error': msg}), 409) if request.is_json else (flash(msg, 'error'), redirect(url_for('signup')))[1]

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        if request.is_json:
            return jsonify({'message': 'Account created successfully', 'username': user.username}), 201
        return redirect(url_for('index'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({'message': 'Login successful', 'username': user.username}), 200
            return redirect(url_for('index'))
        msg = 'Invalid email or password.'
        return (jsonify({'error': msg}), 401) if request.is_json else (flash(msg, 'error'), redirect(url_for('login')))[1]
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/bookmarks')
@login_required
def bookmarks_page():
    return render_template('bookmarks.html')

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/api/search')
def api_search():
    """Search for research papers using the paper_fetcher module."""
    from paper_fetcher import search_papers
    query = request.args.get('q', '').strip()
    source = request.args.get('source', 'arxiv')
    max_results = request.args.get('max', 10, type=int)

    if not query:
        return jsonify({'error': 'Query parameter "q" is required.'}), 400

    results = search_papers(query, source=source, max_results=max_results)
    return jsonify({'query': query, 'source': source, 'count': len(results), 'papers': results})


@app.route('/api/bookmarks', methods=['GET'])
@login_required
def api_get_bookmarks():
    """Get all bookmarks for the current user."""
    bmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.saved_at.desc()).all()
    return jsonify({'bookmarks': [
        {
            'id': b.id,
            'paper_id': b.paper_id,
            'title': b.title,
            'authors': b.authors,
            'summary': b.summary,
            'pdf_url': b.pdf_url,
            'source': b.source,
            'saved_at': b.saved_at.isoformat()
        } for b in bmarks
    ]})


@app.route('/api/bookmarks', methods=['POST'])
@login_required
def api_add_bookmark():
    """Add a bookmark for the current user."""
    data = request.get_json()
    if not data or not data.get('paper_id') or not data.get('title'):
        return jsonify({'error': 'paper_id and title are required.'}), 400

    existing = Bookmark.query.filter_by(user_id=current_user.id, paper_id=data['paper_id']).first()
    if existing:
        return jsonify({'message': 'Already bookmarked.'}), 200

    bookmark = Bookmark(
        user_id=current_user.id,
        paper_id=data['paper_id'],
        title=data['title'],
        authors=data.get('authors', ''),
        summary=data.get('summary', ''),
        pdf_url=data.get('pdf_url', ''),
        source=data.get('source', 'arxiv')
    )
    db.session.add(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmarked successfully.', 'id': bookmark.id}), 201


@app.route('/api/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def api_remove_bookmark(bookmark_id):
    """Remove a bookmark for the current user."""
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first()
    if not bookmark:
        return jsonify({'error': 'Bookmark not found.'}), 404
    db.session.delete(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmark removed.'})


@app.route('/api/bookmarks/check/<path:paper_id>')
@login_required
def api_check_bookmark(paper_id):
    """Check if a paper is bookmarked by the current user."""
    bookmark = Bookmark.query.filter_by(user_id=current_user.id, paper_id=paper_id).first()
    return jsonify({'bookmarked': bookmark is not None, 'bookmark_id': bookmark.id if bookmark else None})


@app.route('/api/me')
def api_me():
    """Return current user info (or anonymous)."""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username, 'email': current_user.email})
    return jsonify({'authenticated': False})


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
