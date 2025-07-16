from app import create_app
from app.extensions import db
from app.models import WorkspaceDocument

# Create a Flask application context
app = create_app()

with app.app_context():
    # Create tables that don't exist yet
    db.create_all()
    print("Database schema updated successfully!")
    
    # Check if the workspace_documents table was created
    result = db.session.execute(db.text('SELECT name FROM sqlite_master WHERE type="table" AND name="workspace_documents"'))
    row = result.first()
    if row:
        print("workspace_documents table exists.")
    else:
        print("Warning: workspace_documents table was not created!")
