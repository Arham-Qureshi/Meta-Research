"""
extensions.py — Shared Flask extension instances.

Centralises db and login_manager so every module can import from here
instead of from app.py, eliminating circular-import issues.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
