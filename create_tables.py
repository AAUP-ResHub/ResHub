"""
Script to create the necessary database tables for ResHub messaging and notifications
"""
from app import create_app
from app.extensions import db
from app.models import User, Message, Notification
import sqlite3
import os

def create_notifications_table():
    """Create the notifications table in the database if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create notifications table with SQLAlchemy
            print("Creating notification and message tables...")
            db.create_all()
            print("Tables created successfully!")
            return True
        except Exception as e:
            print(f"Error creating tables with SQLAlchemy: {str(e)}")
            
            # Fallback to direct SQLite approach
            try:
                print("Trying direct SQLite approach...")
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri[10:]  # Remove sqlite:///
                    print(f"Using database at: {db_path}")
                    
                    # Make sure the directory exists
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir)
                    
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Check if notifications table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
                    if cursor.fetchone() is None:
                        print("Creating notifications table...")
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
                    
                    # Check if messages table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
                    if cursor.fetchone() is None:
                        print("Creating messages table...")
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
                    conn.close()
                    print("Tables created successfully using SQLite directly!")
                    return True
                else:
                    print("Database is not SQLite, cannot create tables directly")
                    return False
            except Exception as e:
                print(f"Error creating tables with SQLite directly: {str(e)}")
                return False

if __name__ == "__main__":
    create_notifications_table()
