import os
from flask import Flask

# Import extensions
from app.extensions import db, migrate, login_manager, cors

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_pyfile('config.py', silent=True)
    
    # Initialize extensions
    db.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
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
