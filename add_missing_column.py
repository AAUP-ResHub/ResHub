#!/usr/bin/env python
"""
Database Schema Fix Utility: Missing Columns Addition

This script was created to resolve SQLAlchemy OperationalErrors caused by a mismatch 
between the model definitions in the application code and the actual database schema.

Problem:
When attempting to upload research papers, the application encountered errors because
the 'research_papers' table in the database was missing several columns that were defined
in the ResearchPaper model class:
- publish_date (Date column for when the paper was published)
- file_path (String column for the path to the uploaded PDF file)
- keywords (String column for paper tags/keywords)

Solution:
This script directly modifies the SQLite database to add these missing columns without
requiring the Flask-Migrate system, which was encountering issues with the FTS5 virtual tables.
It's part of a series of fixes to ensure compatibility between the ORM models and the 
actual database structure.

Context:
Similar schema mismatches were previously fixed for the workspace_files table
(adding s3_object_key, description, size_bytes, and content_type columns).
This is a continuation of that database schema alignment work.
"""

import os
import sqlite3
from datetime import datetime

# Path to your SQLite database file
# Pointing to the instance directory where Flask typically stores the database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def add_missing_columns():
    """Add missing columns to research_papers table in SQLite database"""
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the research_papers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='research_papers';")
        if not cursor.fetchone():
            print("Error: research_papers table does not exist!")
            return False
            
        # Get current columns in the table
        cursor.execute(f"PRAGMA table_info('research_papers');")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Add missing columns if they don't exist
        missing_columns = []
        if 'publish_date' not in columns:
            missing_columns.append("publish_date DATE")
        
        if 'file_path' not in columns:
            missing_columns.append("file_path VARCHAR(500)")
            
        if 'keywords' not in columns:
            missing_columns.append("keywords VARCHAR(255)")
        
        # Execute ALTER TABLE statements for each missing column
        for column_def in missing_columns:
            column_name = column_def.split()[0]
            try:
                print(f"Adding column: {column_def}")
                cursor.execute(f"ALTER TABLE research_papers ADD COLUMN {column_def};")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column '{column_name}' already exists")
                else:
                    print(f"Error adding column '{column_name}': {e}")
                    
        conn.commit()
        print("Database update completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_missing_columns()
