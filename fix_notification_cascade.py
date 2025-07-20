#!/usr/bin/env python3
"""
Migration script to fix notification foreign key cascade behavior
"""

import sqlite3
import os
from app import create_app
from app.extensions import db

def fix_notification_foreign_keys():
    """Fix foreign key constraints for notifications table"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Fixing Notification Foreign Key Constraints ===")
            
            # Get the database path
            db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            if not db_path:
                print("Error: Could not determine database path")
                return False
                
            print(f"Working with database: {db_path}")
            
            # Connect to SQLite directly
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print("\n1. Creating backup of notifications table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications_backup AS 
                SELECT * FROM notifications
            """)
            
            print("2. Dropping existing notifications table...")
            cursor.execute("DROP TABLE IF EXISTS notifications")
            
            print("3. Creating new notifications table with proper foreign key constraints...")
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
            
            print("4. Restoring data from backup...")
            # Only restore notifications where the referenced users still exist
            cursor.execute("""
                INSERT INTO notifications 
                SELECT n.* FROM notifications_backup n
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
            
            print("5. Creating indexes...")
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
            
            print("6. Cleaning up backup table...")
            cursor.execute("DROP TABLE notifications_backup")
            
            conn.commit()
            conn.close()
            
            print(f"✅ Successfully fixed notification foreign key constraints!")
            print(f"   Restored {restored_count} valid notifications")
            print(f"   Invalid notifications (referencing non-existent users) were removed")
            
            return True
            
        except Exception as e:
            print(f"❌ Error fixing foreign key constraints: {e}")
            import traceback
            traceback.print_exc()
            return False

def update_model_definition():
    """Update the notification model in models.py"""
    
    print("\n=== Updating Notification Model Definition ===")
    
    try:
        models_file = "d:/Senior/Senior2/ResHub/app/models.py"
        
        # Read the current models.py
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the foreign key definitions
        old_recipient_fk = "recipient_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)"
        new_recipient_fk = "recipient_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id', ondelete='CASCADE'), nullable=False)"
        
        old_actor_fk = "actor_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=True)"
        new_actor_fk = "actor_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id', ondelete='CASCADE'), nullable=True)"
        
        if old_recipient_fk in content:
            content = content.replace(old_recipient_fk, new_recipient_fk)
            print("✅ Updated recipient foreign key definition")
        else:
            print("⚠️ Could not find recipient foreign key definition to update")
        
        if old_actor_fk in content:
            content = content.replace(old_actor_fk, new_actor_fk)
            print("✅ Updated actor foreign key definition")
        else:
            print("⚠️ Could not find actor foreign key definition to update")
        
        # Write back the updated content
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Model definition updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating model definition: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Notification Foreign Key Cascade Fix")
    print("=" * 40)
    
    # First update the model definition
    if update_model_definition():
        print("\n" + "=" * 40)
        
        # Then fix the database schema
        success = fix_notification_foreign_keys()
        
        if success:
            print("\n🎉 All fixes completed successfully!")
            print("\nThe notification foreign key constraints have been updated to use CASCADE deletion.")
            print("This means that when a user is deleted, their notifications will be automatically deleted too.")
        else:
            print("\n❌ Database fix failed. Please check the errors above.")
    else:
        print("\n❌ Model update failed. Database fix was skipped.")
