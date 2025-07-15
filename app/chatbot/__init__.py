from flask import Blueprint

# Create Blueprint with url_prefix
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Import routes after blueprint definition to avoid circular imports
from app.chatbot import routes

# Import feature flags module
from app.chatbot import feature_flags

# Function to initialize all chatbot-related components with the app
def init_app(app):
    """Initialize all chatbot components with the Flask app"""
    # Register the chatbot blueprint
    app.register_blueprint(chatbot_bp)
    
    # Initialize feature flags
    feature_flags.init_app(app)
