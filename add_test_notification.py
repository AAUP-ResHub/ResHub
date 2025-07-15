"""
Script to add a test notification to demonstrate the notification badge
"""
import sqlite3
from datetime import datetime

def add_test_notification():
    # Connect to SQLite database
    conn = sqlite3.connect('instance/resHub.db')
    cursor = conn.cursor()
    
    # Add test notification for user ID 1
    try:
        cursor.execute('''
        INSERT INTO notifications 
        (user_id, message, timestamp, is_read, notification_type, related_id) 
        VALUES (1, 'Test notification for badge display', ?, 0, 'system', 1)
        ''', (datetime.utcnow(),))
        
        conn.commit()
        print("Successfully added test notification")
        
    except Exception as e:
        print(f"Error adding test notification: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    add_test_notification()
