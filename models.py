from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship(
        'Bookmark', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    collections = db.relationship(
        'Collection', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    color = db.Column(db.String(7), default='#6366f1')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship('Bookmark', backref='collection', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_user_collection_name'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at.isoformat(),
            'bookmark_count': len(self.bookmarks),
        }

    def __repr__(self):
        return f'<Collection {self.name}>'

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=True)
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
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'summary': self.summary,
            'pdf_url': self.pdf_url,
            'source': self.source,
            'saved_at': self.saved_at.isoformat(),
            'collection_id': self.collection_id,
        }

    def __repr__(self):
        return f'<Bookmark {self.paper_id}>'

class GraphCache(db.Model):
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

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_query = db.Column(db.String(512), nullable=False)
    source = db.Column(db.String(64), default='all')
    result_count = db.Column(db.Integer, default=0)
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'query': self.search_query,
            'source': self.source,
            'result_count': self.result_count,
            'searched_at': self.searched_at.isoformat(),
        }

    def __repr__(self):
        return f'<SearchHistory {self.search_query[:30]}>'

class PaperView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    paper_id = db.Column(db.String(256), nullable=False)
    title = db.Column(db.String(512), default='')
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'title': self.title,
            'viewed_at': self.viewed_at.isoformat(),
        }

    def __repr__(self):
        return f'<PaperView {self.paper_id}>'
