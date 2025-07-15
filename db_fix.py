"""
Quick database fix script to update SQLite schema for notifications
"""
from app import create_app
from app.extensions import db
import sqlite3
import os

def fix_database():
    # Get the SQLite database path from the app config
    app = create_app()
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        if not db_path:
            print("Error: Cannot determine database path")
            return False
        
        # If using relative path
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), db_path)
        
        print(f"Using database at: {db_path}")
        
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if notifications table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
            if cursor.fetchone() is None:
                print("Notifications table doesn't exist, creating it...")
                cursor.execute('''
                CREATE TABLE notifications (
                    notification_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT 0,
                    notification_type VARCHAR(50),
                    related_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')
                print("Created notifications table")
            else:
                # Check if user_id column exists
                cursor.execute("PRAGMA table_info(notifications)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'user_id' not in columns:
                    print("Adding user_id column to notifications table...")
                    # SQLite doesn't support direct ALTER TABLE ADD CONSTRAINT
                    # We need to recreate the table
                    cursor.execute("ALTER TABLE notifications ADD COLUMN user_id INTEGER")
                    print("Added user_id column")
                else:
                    print("user_id column already exists")
                
                # Add other missing columns if needed
                if 'timestamp' not in columns:
                    cursor.execute("ALTER TABLE notifications ADD COLUMN timestamp DATETIME")
                if 'notification_type' not in columns:
                    cursor.execute("ALTER TABLE notifications ADD COLUMN notification_type VARCHAR(50)")
                if 'related_id' not in columns:
                    cursor.execute("ALTER TABLE notifications ADD COLUMN related_id INTEGER")
                if 'is_read' not in columns:
                    cursor.execute("ALTER TABLE notifications ADD COLUMN is_read BOOLEAN DEFAULT 0")
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
            print("Database schema update completed successfully")
            return True
        except Exception as e:
            print(f"Error updating database: {str(e)}")
            return False

if __name__ == "__main__":
    fix_database()
