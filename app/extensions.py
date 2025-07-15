"""
Extensions module.
Each extension is initialized in the app factory located in app/__init__.py
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

# Create extension objects
from sqlalchemy.sql import text

# Initialize SQLAlchemy with health check using explicit text() wrapper
class FixedSQLAlchemy(SQLAlchemy):
    def __init__(self, *args, **kwargs):
        # Set up SQLAlchemy to use future=True for 2.0 compatibility
        kwargs.setdefault('engine_options', {})
        kwargs['engine_options'].setdefault('future', True)
        super().__init__(*args, **kwargs)
    
    # We don't need to patch execute anymore since we're using Session.execute with text()
    # in our application code directly where needed

db = FixedSQLAlchemy()
login_manager = LoginManager()
cors = CORS()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
