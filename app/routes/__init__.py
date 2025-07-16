# Make the routes directory a proper Python package
from app.routes.main_routes import main_bp
# Removed document_bp import since it depends on WorkspaceDocument model
