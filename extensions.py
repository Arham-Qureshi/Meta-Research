from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

cors = CORS()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['200 per hour', '50 per minute'],
    storage_uri='memory://',
)
