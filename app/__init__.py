import os
from flask import Flask

# Import extensions
from app.extensions import db, login_manager, cors, csrf
from flask_migrate import Migrate
from flask_admin import Admin

# Import security configurations
from app.config.security import configure_csp
# Import custom admin helpers
from app.admin_helpers import register_template_helpers

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
    
    # Initialize Flask-Admin
    admin = Admin(app, name='ResHub Admin Dashboard', template_mode='bootstrap4')
    
    # Exempt Flask-Admin views from CSRF protection
    # This is needed because Flask-Admin handles CSRF differently
    csrf.exempt(admin.index_view.blueprint)
    
    # Register custom template helpers
    register_template_helpers(app)
    
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
    from app.workspaces import workspaces_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(paper_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(workspaces_bp)
    
    # Import models and admin views after initialization to avoid circular imports
    with app.app_context():
        from .models import User, RegisteredUser, SiteSetting, CollaborationWorkspace, WorkspaceDocument, ResearchPaper, ForumTopic, ForumPost, SystemLog
        from .admin import (AdminModelView, UserModelView, RegisteredUserModelView, SiteSettingModelView, 
                           ForumPostModelView, AnnouncementView, SystemLogView, CollaborationWorkspaceModelView,
                           WorkspaceDocumentModelView, AdminRegistrationView)

        # Add views for models to the admin panel
        admin.add_view(UserModelView(User, db.session, category='User Management'))
        admin.add_view(RegisteredUserModelView(RegisteredUser, db.session, name="User Profiles", category='User Management'))
        
        admin.add_view(CollaborationWorkspaceModelView(CollaborationWorkspace, db.session, name="Workspaces", category='Content Management'))
        admin.add_view(WorkspaceDocumentModelView(WorkspaceDocument, db.session, name="Workspace Docs", category='Content Management'))
        admin.add_view(AdminModelView(ResearchPaper, db.session, category='Content Management'))
        admin.add_view(AdminModelView(ForumTopic, db.session, category='Content Management'))
        admin.add_view(ForumPostModelView(ForumPost, db.session, category='Content Management'))

        admin.add_view(SiteSettingModelView(SiteSetting, db.session, name="Site Settings", category='Configuration'))
        admin.add_view(SystemLogView(SystemLog, db.session, name="System Logs", category='Site Health'))
        admin.add_view(AnnouncementView(name='Send Announcement', endpoint='announcements', category='Tools'))
        admin.add_view(AdminRegistrationView(name='Create Admin Profile', endpoint='create_admin', category='Tools'))
    
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
