import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from whitenoise import WhiteNoise

app = Flask(__name__)
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application. Please configure it in your environment variables.")

basedir = os.path.abspath(os.path.dirname(__file__))

database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Vercel Postgres
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'meta_research.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

from extensions import db, login_manager, cors, limiter

db.init_app(app)
login_manager.init_app(app)
cors.init_app(app, resources={r'/api/*': {'origins': '*'}})
limiter.init_app(app)

from errors import register_error_handlers
register_error_handlers(app)

import models

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

from routes import register_routes
register_routes(app)

from citation_graph import create_blueprint
app.register_blueprint(create_blueprint())

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
