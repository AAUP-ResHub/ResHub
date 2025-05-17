from flask import Flask
from flask_migrate import Migrate
from config import Config
from models import db # Import the db instance from models.py

# Import all models so Flask-Migrate can find them
from models import (
    User, Admin, RegisteredUser, PremiumUser,
    SystemLog, ForumPost, ResearchPaper, PaperMetrics, Notification,
    JournalFinderServiceConfig, CollaborationWorkspace, WorkspaceMember,
    WorkspaceFile, AIDataset, RecommendationEngineConfig
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate = Migrate(app, db) # Initialize Flask-Migrate

    # You can register blueprints or routes here if needed for a full app
    @app.route('/')
    def hello():
        return "Hello, Research App Database is (being) set up!"

    return app

# This allows running 'flask run' or 'python app.py'
# For 'flask run', Flask CLI needs to know where the app is.
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
