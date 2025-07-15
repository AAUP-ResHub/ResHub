"""
Database migration script to add scheduled message fields to the Message model
and create the MessageRecipient table for multi-recipient support.
"""

import sqlite3
import os
from datetime import datetime

# Path to database
DB_PATH = os.path.join('instance', 'resHub.db')

def migrate():
    """Execute the database migration"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Starting migration for scheduled messages...")
    
    # Check if the columns already exist
    cursor.execute("PRAGMA table_info(messages)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add is_scheduled column if it doesn't exist
    if 'is_scheduled' not in columns:
        print("Adding is_scheduled column to messages table...")
        cursor.execute("ALTER TABLE messages ADD COLUMN is_scheduled BOOLEAN DEFAULT 0")
    
    # Add status column if it doesn't exist
    if 'status' not in columns:
        print("Adding status column to messages table...")
        cursor.execute("ALTER TABLE messages ADD COLUMN status VARCHAR(20) DEFAULT 'pending'")
    
    # Update existing scheduled messages
    print("Updating existing scheduled messages...")
    cursor.execute("""
        UPDATE messages 
        SET is_scheduled = 1, 
            status = 'pending' 
        WHERE scheduled_for IS NOT NULL 
          AND scheduled_for > datetime('now')
    """)
    
    # Update past scheduled messages as sent
    cursor.execute("""
        UPDATE messages 
        SET is_scheduled = 0, 
            status = 'sent' 
        WHERE scheduled_for IS NOT NULL 
          AND scheduled_for <= datetime('now')
    """)
    
    # Check if message_recipients table exists
    cursor.execute("""
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' 
          AND name='message_recipients'
    """)
    
    if not cursor.fetchone():
        print("Creating message_recipients table...")
        cursor.execute("""
            CREATE TABLE message_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages (message_id) ON DELETE CASCADE,
                FOREIGN KEY (recipient_id) REFERENCES users (user_id)
            )
        """)
        
        # Populate message_recipients with data from existing scheduled messages
        print("Populating message_recipients table with existing data...")
        cursor.execute("""
            INSERT INTO message_recipients (message_id, recipient_id)
            SELECT message_id, receiver_id
            FROM messages
            WHERE is_scheduled = 1
        """)
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
