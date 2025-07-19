import os
from flask import Flask

# Import extensions
from app.extensions import db, login_manager, cors, csrf
from flask_migrate import Migrate

# Import security configurations
from app.config.security import configure_csp

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_pyfile('config.py', silent=True)
    
    # Initialize extensions
    db.init_app(app)
    cors.init_app(app)
    csrf.init_app(app)
    
    # Initialize migrations
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.get_by_id(user_id)
    
    # Register blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    from app.paper import paper_bp
    from app.forum import forum_bp
    from app.errors import errors_bp
    from app.search import search_bp
    from app.chatbot import chatbot_bp
    from app.workspaces import workspaces_bp
    from app.routes.notification_routes import notification_bp
    from app.routes.notification_test_route import notification_test_bp
    from app.routes.integration_test_route import integration_test_bp
    # Import new blueprints from teammate1
    from app.citation import citation_bp
    from app.messaging import messaging_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(paper_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(workspaces_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(notification_test_bp)
    app.register_blueprint(integration_test_bp)
    # Register new blueprints from teammate1
    app.register_blueprint(citation_bp, url_prefix='/citation')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    
    # Context processors for template variables
    @app.context_processor
    def inject_year():
        from datetime import datetime, timezone
        return dict(current_year=datetime.now(timezone.utc).year)
        
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=lambda: generate_csrf())
    
    # Apply security configurations
    configure_csp(app)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Set up migrations directory if it doesn't exist
        if not os.path.exists('migrations'):
            from flask_migrate import init, migrate
            init()
            migrate('Initial migration')

    return app
