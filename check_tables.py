"""
Script to check database tables and create missing ones
"""
import sqlite3
import os

def check_database():
    # Check if the database file exists
    db_path = 'instance/resHub.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist")
        return
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    print("Checking existing tables...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Check if messages table exists and create it if not
    if 'messages' not in [t[0] for t in tables]:
        print("\nCreating messages table...")
        cursor.execute('''
        CREATE TABLE messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            parent_id INTEGER,
            scheduled_for DATETIME
        )
        ''')
        conn.commit()
        print("Messages table created successfully")
    
    # Check if notifications table exists and create it if not
    if 'notifications' not in [t[0] for t in tables]:
        print("\nCreating notifications table...")
        cursor.execute('''
        CREATE TABLE notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            notification_type VARCHAR(50),
            related_id INTEGER
        )
        ''')
        conn.commit()
        print("Notifications table created successfully")
    
    # Check table columns
    print("\nChecking table columns:")
    for table_name in ['messages', 'notifications']:
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n{table_name} table columns:")
            for col in columns:
                print(f"- {col[1]} ({col[2]})")
        except Exception as e:
            print(f"Error checking {table_name} table: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
