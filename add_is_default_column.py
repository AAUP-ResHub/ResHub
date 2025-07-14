from app import create_app, db
from flask_migrate import upgrade
from alembic import op
import sqlalchemy as sa

# Create the Flask application context
app = create_app()

def add_column():
    """Directly add is_default column to workspace_documents table"""
    with app.app_context():
        try:
            # Try to execute the raw SQL to add the column
            db.session.execute(sa.text(
                "ALTER TABLE workspace_documents ADD COLUMN is_default BOOLEAN DEFAULT 0"
            ))
            db.session.commit()
            print("Successfully added is_default column to workspace_documents table")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding column: {str(e)}")
            # If there's an error, try to run all migrations
            print("Attempting to run all pending migrations...")
            upgrade()

if __name__ == '__main__':
    add_column()
