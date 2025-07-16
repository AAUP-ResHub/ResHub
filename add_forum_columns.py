#!/usr/bin/env python
"""
Forum Database Fix Utility

This script was created to fix the database schema mismatch for the forum functionality.

Problem:
When accessing the forum, the application encounters an OperationalError:
"sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: forum_posts.is_edited"

The error occurs because the code is trying to access the 'is_edited' column in the forum_posts table,
but this column doesn't exist in the actual database schema, despite being defined in the ForumPost model.

Solution:
This script adds the missing 'is_edited' column to the forum_posts table by directly 
executing an ALTER TABLE command on the SQLite database.

Context:
This continues our database schema alignment work, similar to how we fixed missing columns
in the research_papers and workspace_files tables. These fixes address discrepancies between
the SQLAlchemy model definitions and the actual database schema that were causing operational errors.
"""

import os
import sqlite3

# Path to your SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def add_forum_columns():
    """Add missing is_edited column to forum_posts table in SQLite database"""
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the forum_posts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forum_posts';")
        if not cursor.fetchone():
            print("Error: forum_posts table does not exist!")
            return False
            
        # Get current columns in the table
        cursor.execute(f"PRAGMA table_info('forum_posts');")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Current forum_posts columns: {columns}")
        
        # Add is_edited column if it doesn't exist
        if 'is_edited' not in columns:
            print("Adding 'is_edited' column to forum_posts table...")
            try:
                # Adding is_edited as a boolean column with default value 0 (False)
                cursor.execute("ALTER TABLE forum_posts ADD COLUMN is_edited BOOLEAN DEFAULT 0;")
                print("Successfully added 'is_edited' column!")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("Column 'is_edited' already exists")
                else:
                    print(f"Error adding column 'is_edited': {e}")
                    return False
        else:
            print("Column 'is_edited' already exists in forum_posts table.")
            
        conn.commit()
        print("Forum database update completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_forum_columns()
