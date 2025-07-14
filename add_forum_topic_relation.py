#!/usr/bin/env python
"""
Forum Topic Relation Fix Utility

This script was created to fix the forum table relationships by adding the missing topic_id foreign key.

Problem:
After adding the 'is_edited' column, we encountered a new error:
"sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: forum_posts.topic_id"

This indicates that the forum_posts table is missing the 'topic_id' column that should link
forum posts to their parent topics, which is essential for the forum functionality.

Solution:
This script adds the missing 'topic_id' column to the forum_posts table, allowing proper 
relationships between posts and topics in the forum system.

Context:
This is the third fix in our database schema alignment work:
1. First, we fixed the research_papers table and FTS functionality
2. Then, we added the 'is_edited' column to forum_posts
3. Now, we're adding the critical relationship column 'topic_id' to properly link posts to topics

These incremental fixes address discrepancies between the SQLAlchemy model definitions 
and the actual database schema, bringing the application back to full functionality.
"""

import os
import sqlite3

# Path to your SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def add_topic_relation():
    """Add missing topic_id column to forum_posts table in SQLite database"""
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
        
        # Add topic_id column if it doesn't exist
        if 'topic_id' not in columns:
            print("Adding 'topic_id' column to forum_posts table...")
            try:
                # Adding topic_id as an integer foreign key column
                # Note: SQLite doesn't enforce foreign key constraints by default
                cursor.execute("ALTER TABLE forum_posts ADD COLUMN topic_id INTEGER;")
                print("Successfully added 'topic_id' column!")
                
                # Check if we have forum_topics table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forum_topics';")
                if cursor.fetchone():
                    print("INFO: To fully restore functionality, you may need to manually update existing posts with the correct topic_id values.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("Column 'topic_id' already exists")
                else:
                    print(f"Error adding column 'topic_id': {e}")
                    return False
        else:
            print("Column 'topic_id' already exists in forum_posts table.")
            
        conn.commit()
        print("Forum topic relation fix completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_topic_relation()
