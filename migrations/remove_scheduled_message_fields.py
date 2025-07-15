"""
Database migration script to remove scheduled message fields from the Message model
and drop the MessageRecipient table as scheduled messaging feature is being removed.
"""

import sqlite3
import os
from datetime import datetime

# Path to database
DB_PATH = os.path.join('instance', 'resHub.db')

def migrate():
    """Execute the database migration to remove scheduled message functionality"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Starting migration to remove scheduled message functionality...")
    
    # Check if the columns exist
    cursor.execute("PRAGMA table_info(messages)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Begin transaction for safety
    conn.execute('BEGIN TRANSACTION')
    
    try:
        # Remove is_scheduled column if it exists
        if 'is_scheduled' in columns:
            print("Removing is_scheduled column from messages table...")
            # SQLite doesn't support DROP COLUMN directly, so we need to:
            # 1. Create a new table without the column
            # 2. Copy the data
            # 3. Drop the old table
            # 4. Rename the new table
            
            # Create new table without is_scheduled column
            cursor.execute("""
                CREATE TABLE messages_new (
                    message_id INTEGER PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    parent_id INTEGER,
                    FOREIGN KEY (sender_id) REFERENCES users (user_id),
                    FOREIGN KEY (receiver_id) REFERENCES users (user_id),
                    FOREIGN KEY (parent_id) REFERENCES messages (message_id)
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO messages_new (
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                )
                SELECT 
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                FROM messages
            """)
            
            # Drop old table
            cursor.execute("DROP TABLE messages")
            
            # Rename new table to messages
            cursor.execute("ALTER TABLE messages_new RENAME TO messages")
            
            print("Removed is_scheduled column from messages table")
        
        # Check if the status column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Remove status column if it exists
        if 'status' in columns:
            print("Removing status column from messages table...")
            # Since we recreated the table already, if status still exists we need to do it again
            # Create new table without status column
            cursor.execute("""
                CREATE TABLE messages_new (
                    message_id INTEGER PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    parent_id INTEGER,
                    FOREIGN KEY (sender_id) REFERENCES users (user_id),
                    FOREIGN KEY (receiver_id) REFERENCES users (user_id),
                    FOREIGN KEY (parent_id) REFERENCES messages (message_id)
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO messages_new (
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                )
                SELECT 
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                FROM messages
            """)
            
            # Drop old table
            cursor.execute("DROP TABLE messages")
            
            # Rename new table to messages
            cursor.execute("ALTER TABLE messages_new RENAME TO messages")
            
            print("Removed status column from messages table")
        
        # Check if the scheduled_for column exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Remove scheduled_for column if it exists
        if 'scheduled_for' in columns:
            print("Removing scheduled_for column from messages table...")
            # Create new table without scheduled_for column
            cursor.execute("""
                CREATE TABLE messages_new (
                    message_id INTEGER PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    parent_id INTEGER,
                    FOREIGN KEY (sender_id) REFERENCES users (user_id),
                    FOREIGN KEY (receiver_id) REFERENCES users (user_id),
                    FOREIGN KEY (parent_id) REFERENCES messages (message_id)
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO messages_new (
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                )
                SELECT 
                    message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id
                FROM messages
            """)
            
            # Drop old table
            cursor.execute("DROP TABLE messages")
            
            # Rename new table to messages
            cursor.execute("ALTER TABLE messages_new RENAME TO messages")
            
            print("Removed scheduled_for column from messages table")
        
        # Check if message_recipients table exists
        cursor.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' 
              AND name='message_recipients'
        """)
        
        if cursor.fetchone():
            print("Dropping message_recipients table...")
            cursor.execute("DROP TABLE message_recipients")
            print("Dropped message_recipients table successfully")
        
        # Commit the transaction
        conn.commit()
        print("Migration completed successfully!")
    
    except Exception as e:
        # Roll back in case of error
        conn.rollback()
        print(f"Error during migration: {str(e)}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
