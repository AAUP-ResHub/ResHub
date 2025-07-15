"""
Script to add a test unread message to demonstrate the unread message badge
"""
import sqlite3
from datetime import datetime

def add_test_message():
    # Connect to SQLite database
    conn = sqlite3.connect('instance/resHub.db')
    cursor = conn.cursor()
    
    # Add test message from user ID 2 to user ID 1
    try:
        cursor.execute("""
        INSERT INTO messages 
        (sender_id, receiver_id, content, timestamp, is_read) 
        VALUES (2, 1, 'Test message for unread badge', ?, 0)
        """, (datetime.utcnow(),))
        
        conn.commit()
        print("Successfully added test unread message")
        
    except Exception as e:
        print(f"Error adding test message: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    add_test_message()
