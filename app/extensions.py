"""
Extensions module.
Each extension is initialized in the app factory located in app/__init__.py
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

# Create extension objects
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cors = CORS()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
