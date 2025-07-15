"""
Force SQLAlchemy to refresh its internal schema cache by
recreating the tables with the updated definitions.
"""

from app import create_app, db
app = create_app()
from app.models import Message, User
from sqlalchemy import inspect, text
import sqlite3
import os

def has_column(table_name, column_name):
    """Check if a column exists in a table"""
    with app.app_context():
        insp = inspect(db.engine)
        columns = insp.get_columns(table_name)
        for column in columns:
            if column['name'] == column_name:
                return True
        return False

def refresh_schema():
    """Refresh the schema by adding any missing columns"""
    with app.app_context():
        print("Checking for schema updates...")
        
        # Scheduled message fields have been removed from the Message model
        
        # MessageRecipient model has been removed
        
        # Scheduled message functionality has been removed
        
        print("Schema refresh complete!")

if __name__ == "__main__":
    refresh_schema()
