"""
app.py — Flask application factory & bootstrap.

This is the single entry point. It creates the Flask app, initialises
extensions, registers all blueprints, and creates DB tables.

All business logic lives in services/.
All routes live in routes/ and citation_graph/.
All models live in models.py.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask

# ── Create app ──────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'meta_research.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── Init extensions ─────────────────────────────────────────
from extensions import db, login_manager
db.init_app(app)
login_manager.init_app(app)

# ── Import models so tables are known to SQLAlchemy ─────────
import models  # noqa: F401

# ── User loader (required by Flask-Login) ───────────────────
@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

# ── Register all route blueprints ───────────────────────────
from routes import register_routes
register_routes(app)

# ── Register citation graph blueprint ───────────────────────
from citation_graph import create_blueprint
app.register_blueprint(create_blueprint())

# ── Create DB tables ────────────────────────────────────────
with app.app_context():
    db.create_all()

# ── Run ─────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
