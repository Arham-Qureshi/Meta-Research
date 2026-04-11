import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

basedir = os.path.abspath(os.path.dirname(__file__))
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
