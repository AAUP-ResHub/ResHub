"""
ResHub Feature Flags Module

This module manages feature flags for the ResHub application,
allowing for gradual rollout of new features and A/B testing.
"""

from flask import Blueprint, jsonify, current_app

# Create a Blueprint for feature flag routes
feature_flags_bp = Blueprint('feature_flags', __name__)

# Default feature flags
DEFAULT_FLAGS = {
    # Core UI feature flag
    'USE_NEW_CHATBOT_UI': False,
    
    # Component-specific feature flags
    'USE_COMPONENT_API_SERVICE': False,
    'USE_COMPONENT_STORE': False,
    'USE_CHAT_INPUT_COMPONENT': False,
    'USE_MESSAGE_COMPONENT': False,
    'USE_SESSION_LIST_COMPONENT': False,
    'USE_CHAT_HISTORY_COMPONENT': False,
    
    # Development and testing flags
    'DEV_SHOW_DEBUG_INFO': False,
    'USE_VITE_DEV_SERVER': False
}

def get_feature_flags():
    """
    Get all available feature flags from app config,
    falling back to defaults if not set.
    """
    flags = {}
    
    # Start with default flags
    for flag_name, default_value in DEFAULT_FLAGS.items():
        # Get from app config or use default
        flags[flag_name] = current_app.config.get(flag_name, default_value)
        
    return flags

@feature_flags_bp.route('/api/feature-flags')
def feature_flags_endpoint():
    """Endpoint to fetch current feature flag settings"""
    return jsonify(get_feature_flags())


def init_app(app):
    """
    Initialize the feature flags module with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Register blueprint
    app.register_blueprint(feature_flags_bp)
    
    # Set default flags in app config if not already set
    for flag_name, default_value in DEFAULT_FLAGS.items():
        if flag_name not in app.config:
            app.config[flag_name] = default_value
    
    # Log feature flag status on startup
    if app.debug:
        app.logger.info("Feature flags: %s", get_feature_flags())
