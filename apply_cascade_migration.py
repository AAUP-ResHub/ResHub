#!/usr/bin/env python3
"""
Apply CASCADE foreign key constraints to notifications table
"""

import sqlite3
from app import create_app
from app.extensions import db

def apply_cascade_migration():
    """Apply CASCADE foreign key constraints to notifications table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Applying CASCADE Migration to Notifications Table ===")
            
            # Get database path
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///app.db')
            db_path = db_uri.replace('sqlite:///', '')
            print(f"Working with database: {db_path}")
            
            # Connect to SQLite directly for schema manipulation
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print("\n1. Backing up existing notifications...")
            cursor.execute("DROP TABLE IF EXISTS notifications_migration_backup")
            cursor.execute("""
                CREATE TABLE notifications_migration_backup AS 
                SELECT * FROM notifications
            """)
            
            backup_count = cursor.rowcount
            cursor.execute("SELECT COUNT(*) FROM notifications_migration_backup")
            backup_count = cursor.fetchone()[0]
            print(f"   Backed up {backup_count} notifications")
            
            print("\n2. Dropping existing notifications table...")
            cursor.execute("DROP TABLE notifications")
            
            print("\n3. Creating new notifications table with CASCADE constraints...")
            cursor.execute("""
                CREATE TABLE notifications (
                    notification_id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    sent_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    recipient_registered_user_id INTEGER NOT NULL 
                        REFERENCES registered_users(registered_user_id) ON DELETE CASCADE,
                    action VARCHAR(255) NOT NULL DEFAULT '',
                    object_type VARCHAR(50),
                    object_id INTEGER,
                    actor_registered_user_id INTEGER 
                        REFERENCES registered_users(registered_user_id) ON DELETE CASCADE
                )
            """)
            
            print("\n4. Restoring data from backup...")
            # Only restore notifications where the referenced users still exist
            cursor.execute("""
                INSERT INTO notifications (
                    notification_id, message, is_read, sent_date, 
                    recipient_registered_user_id, action, object_type, 
                    object_id, actor_registered_user_id
                )
                SELECT 
                    n.notification_id, n.message, n.is_read, n.sent_date,
                    n.recipient_registered_user_id, 
                    COALESCE(n.action, '') as action,
                    n.object_type, n.object_id, n.actor_registered_user_id
                FROM notifications_migration_backup n
                WHERE EXISTS (
                    SELECT 1 FROM registered_users ru 
                    WHERE ru.registered_user_id = n.recipient_registered_user_id
                )
                AND (
                    n.actor_registered_user_id IS NULL 
                    OR EXISTS (
                        SELECT 1 FROM registered_users ru2 
                        WHERE ru2.registered_user_id = n.actor_registered_user_id
                    )
                )
            """)
            
            restored_count = cursor.rowcount
            print(f"   Restored {restored_count} valid notifications")
            
            print("\n5. Creating indexes for better performance...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_notifications_recipient_registered_user_id 
                ON notifications (recipient_registered_user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_notifications_sent_date 
                ON notifications (sent_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_notifications_is_read 
                ON notifications (is_read)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_notifications_action 
                ON notifications (action)
            """)
            
            print("\n6. Verifying new schema...")
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notifications'")
            schema = cursor.fetchone()
            
            if schema and 'ON DELETE CASCADE' in schema[0]:
                print("   ✅ CASCADE constraints are now properly configured!")
                print("   Schema preview:")
                schema_lines = schema[0].split('\n')
                for line in schema_lines[:10]:  # Show first 10 lines
                    if line.strip():
                        print(f"   {line.strip()}")
                if len(schema_lines) > 10:
                    print("   ...")
            else:
                print("   ❌ CASCADE constraints were not applied correctly")
                return False
            
            print("\n7. Cleaning up backup table...")
            cursor.execute("DROP TABLE notifications_migration_backup")
            
            # Commit all changes
            conn.commit()
            conn.close()
            
            print(f"\n✅ Migration completed successfully!")
            print(f"   - {backup_count} notifications backed up")
            print(f"   - {restored_count} notifications restored")
            print(f"   - CASCADE delete constraints applied")
            print(f"   - Performance indexes created")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to restore from backup if something went wrong
            try:
                print("\nAttempting to restore from backup...")
                cursor.execute("DROP TABLE IF EXISTS notifications")
                cursor.execute("""
                    CREATE TABLE notifications AS 
                    SELECT * FROM notifications_migration_backup
                """)
                cursor.execute("DROP TABLE notifications_migration_backup")
                conn.commit()
                print("✅ Restored from backup")
            except:
                print("❌ Could not restore from backup")
            
            return False

def test_cascade_behavior():
    """Test that CASCADE delete behavior works correctly"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n=== Testing CASCADE Delete Behavior ===")
            
            from app.models import User, RegisteredUser, Notification
            
            # Create a test user for deletion testing
            test_user = User(
                username='cascade_test_user',
                email='cascade_test@example.com',
                password_hash='test_hash',
                user_type='registered'
            )
            db.session.add(test_user)
            db.session.flush()
            
            # Create registered user profile
            reg_user = RegisteredUser(user_id=test_user.user_id)
            db.session.add(reg_user)
            db.session.flush()
            
            # Create test notifications
            notification1 = Notification(
                message="Test notification 1 - will be cascade deleted",
                recipient_registered_user_id=reg_user.registered_user_id,
                action="test"
            )
            notification2 = Notification(
                message="Test notification 2 - will be cascade deleted", 
                recipient_registered_user_id=reg_user.registered_user_id,
                actor_registered_user_id=reg_user.registered_user_id,
                action="test"
            )
            
            db.session.add(notification1)
            db.session.add(notification2)
            db.session.commit()
            
            print(f"Created test user: {test_user.username}")
            print(f"Created test notifications: {notification1.notification_id}, {notification2.notification_id}")
            
            # Count notifications before deletion
            notifications_before = Notification.query.filter_by(
                recipient_registered_user_id=reg_user.registered_user_id
            ).count()
            print(f"Notifications before deletion: {notifications_before}")
            
            # Delete the user - this should cascade to notifications
            print("\nDeleting test user...")
            db.session.delete(reg_user)
            db.session.delete(test_user)
            db.session.commit()
            
            print("✅ User deletion completed without integrity error!")
            
            # Verify notifications were cascade deleted
            notifications_after = Notification.query.filter_by(
                recipient_registered_user_id=reg_user.registered_user_id
            ).count()
            print(f"Notifications after deletion: {notifications_after}")
            
            if notifications_after == 0:
                print("✅ CASCADE delete worked perfectly! Notifications were automatically deleted.")
                return True
            else:
                print("❌ CASCADE delete did not work. Notifications still exist.")
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Notifications CASCADE Migration Script")
    print("=" * 50)
    
    # Apply the migration
    if apply_cascade_migration():
        print("\n" + "=" * 50)
        
        # Test the cascade behavior
        if test_cascade_behavior():
            print(f"\n🎉 Migration and testing completed successfully!")
            print("\nThe notifications integrity error has been fixed!")
            print("You can now safely delete users from the admin interface.")
        else:
            print(f"\n⚠️ Migration applied but testing failed.")
            print("Please check the database manually.")
    else:
        print(f"\n❌ Migration failed. Please check the errors above.")
