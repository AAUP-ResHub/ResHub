'''
Instructions for integrating the document saving route with your Flask application:

1. Locate your Flask application factory function or main app setup file (usually in app/__init__.py)

2. Import the document blueprint registration function:
   from app.routes.register_routes import register_document_routes

3. Find where you register other blueprints and add:
   register_document_routes(app)

Example for app factory pattern:

def create_app(config=None):
    app = Flask(__name__)
    
    # Load configuration
    
    # Initialize extensions
    
    # Register blueprints
    from app.routes.register_routes import register_document_routes
    register_document_routes(app)
    
    return app
'''

# This is a helper file to explain how to integrate the document saving route
# Follow the instructions above to modify your app's initialization code
