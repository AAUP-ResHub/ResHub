import os
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Create extension instances
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Load configuration
    app.config.from_pyfile('config.py', silent=True)
    
    # Initialize database
    from app.models import db
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.get_by_id(user_id)
    
    # Register blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    
    # Context processor for template variables
    @app.context_processor
    def inject_year():
        from datetime import datetime, timezone
        return dict(current_year=datetime.now(timezone.utc).year)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Set up migrations directory if it doesn't exist
        if not os.path.exists('migrations'):
            from flask_migrate import init, migrate
            init()
            migrate('Initial migration')
    
    return app
