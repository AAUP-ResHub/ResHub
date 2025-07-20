#!/usr/bin/env python3
"""
Test script to verify notification deletion fix
"""

from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, Notification
import sqlite3

def test_notification_deletion():
    """Test that notification deletion works correctly"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Testing Notification Deletion Fix ===")
            
            # Check current database schema
            db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print("1. Checking current notifications table schema...")
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notifications'")
            schema = cursor.fetchone()
            
            if schema:
                print("Current notifications table schema:")
                print(schema[0])
                
                # Check if CASCADE is in the schema
                if 'ON DELETE CASCADE' in schema[0]:
                    print("✅ CASCADE delete is properly configured in database schema")
                else:
                    print("❌ CASCADE delete is NOT configured in database schema")
                    print("   Running database fix...")
                    
                    # Re-run the database fix part
                    fix_database_schema(cursor, conn)
            else:
                print("❌ Notifications table not found!")
                return False
            
            conn.close()
            
            print("\n2. Testing with sample data...")
            
            # Create test user and notification
            test_user = User.query.filter_by(username='test_delete_user').first()
            if not test_user:
                # Create a test user
                test_user = User(
                    username='test_delete_user',
                    email='test_delete@example.com',
                    password_hash='test_hash',
                    user_type='registered'
                )
                db.session.add(test_user)
                db.session.flush()
                
                # Create registered user profile
                reg_user = RegisteredUser(user_id=test_user.user_id)
                db.session.add(reg_user)
                db.session.flush()
                
                # Create a test notification
                notification = Notification(
                    message="Test notification for deletion",
                    recipient_registered_user_id=reg_user.registered_user_id
                )
                db.session.add(notification)
                db.session.commit()
                
                print(f"Created test user {test_user.username} with notification")
            else:
                reg_user = RegisteredUser.query.filter_by(user_id=test_user.user_id).first()
                print(f"Using existing test user {test_user.username}")
            
            # Count notifications before deletion
            notifications_before = Notification.query.filter_by(
                recipient_registered_user_id=reg_user.registered_user_id
            ).count()
            print(f"Notifications for test user before deletion: {notifications_before}")
            
            print("\n3. Testing deletion...")
            
            # Delete the registered user (this should cascade to notifications)
            db.session.delete(reg_user)
            db.session.delete(test_user)
            db.session.commit()
            
            print("✅ User deletion completed without integrity error!")
            
            # Verify notifications were deleted
            notifications_after = Notification.query.filter_by(
                recipient_registered_user_id=reg_user.registered_user_id
            ).count()
            print(f"Notifications for test user after deletion: {notifications_after}")
            
            if notifications_after == 0:
                print("✅ Notifications were properly cascaded and deleted!")
                return True
            else:
                print("❌ Notifications were not deleted (cascade didn't work)")
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False

def fix_database_schema(cursor, conn):
    """Fix the database schema if CASCADE is not properly configured"""
    try:
        print("   Creating backup and recreating notifications table...")
        
        # Create backup
        cursor.execute("CREATE TABLE notifications_backup AS SELECT * FROM notifications")
        
        # Drop and recreate table
        cursor.execute("DROP TABLE notifications")
        cursor.execute("""
            CREATE TABLE notifications (
                notification_id INTEGER PRIMARY KEY,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                sent_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                recipient_registered_user_id INTEGER NOT NULL 
                    REFERENCES registered_users(registered_user_id) ON DELETE CASCADE,
                actor_registered_user_id INTEGER 
                    REFERENCES registered_users(registered_user_id) ON DELETE CASCADE,
                action VARCHAR(50),
                object_type VARCHAR(50),
                object_id INTEGER
            )
        """)
        
        # Restore data
        cursor.execute("""
            INSERT INTO notifications 
            SELECT n.* FROM notifications_backup n
            WHERE EXISTS (
                SELECT 1 FROM registered_users ru 
                WHERE ru.registered_user_id = n.recipient_registered_user_id
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_notifications_recipient_registered_user_id 
            ON notifications (recipient_registered_user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_notifications_sent_date 
            ON notifications (sent_date)
        """)
        
        # Cleanup
        cursor.execute("DROP TABLE notifications_backup")
        conn.commit()
        
        print("   ✅ Database schema fixed!")
        
    except Exception as e:
        print(f"   ❌ Error fixing database schema: {e}")
        raise

if __name__ == "__main__":
    success = test_notification_deletion()
    
    if success:
        print("\n🎉 Notification deletion fix verified successfully!")
        print("You can now safely delete users from the admin interface without integrity errors.")
    else:
        print("\n❌ Fix verification failed. Manual intervention may be required.")
