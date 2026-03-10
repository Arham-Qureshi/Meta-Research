"""
models.py — All SQLAlchemy data models.

Single source of truth for the database schema. Every model inherits
db.Model and lives here so other modules never define ad-hoc tables.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ═══════════════════════════════════════════════════════════════
#  USER
# ═══════════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship(
        'Bookmark', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ═══════════════════════════════════════════════════════════════
#  BOOKMARK
# ═══════════════════════════════════════════════════════════════

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.String(256), nullable=False)
    title = db.Column(db.String(512), nullable=False)
    authors = db.Column(db.String(512))
    summary = db.Column(db.Text)
    pdf_url = db.Column(db.String(512))
    source = db.Column(db.String(64))
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'paper_id', name='uq_user_paper'),
    )

    def to_dict(self) -> dict:
        """Serialise to JSON-friendly dict — reusable across all routes."""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'summary': self.summary,
            'pdf_url': self.pdf_url,
            'source': self.source,
            'saved_at': self.saved_at.isoformat(),
        }

    def __repr__(self):
        return f'<Bookmark {self.paper_id}>'


# ═══════════════════════════════════════════════════════════════
#  GRAPH CACHE
# ═══════════════════════════════════════════════════════════════

class GraphCache(db.Model):
    """Cache citation graph JSON to reduce external API calls."""
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.String(256), nullable=False)
    source = db.Column(db.String(64), nullable=False)
    graph_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('paper_id', 'source', name='uq_paper_source'),
    )

    def __repr__(self):
        return f'<GraphCache {self.paper_id}:{self.source}>'
