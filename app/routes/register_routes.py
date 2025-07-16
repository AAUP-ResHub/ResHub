from flask import Flask
from app.routes.document_routes import document_bp

def register_document_routes(app):
    """Register document-related blueprints with the Flask application."""
    app.register_blueprint(document_bp)
    return app
