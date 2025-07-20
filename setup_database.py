#!/usr/bin/env python3
"""
Database setup and verification script
"""

from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, Notification
import os

def setup_and_verify_database():
    """Setup and verify database tables"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Database Setup and Verification ===")
            
            # Get database path
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/app.db')
            print(f"Database URI: {db_uri}")
            
            if 'sqlite:///' in db_uri:
                db_path = db_uri.replace('sqlite:///', '')
                print(f"Database file path: {db_path}")
                
                # Check if database file exists
                if os.path.exists(db_path):
                    print("✅ Database file exists")
                else:
                    print("❌ Database file does not exist - will be created")
            
            print("\n1. Creating all database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            print("\n2. Verifying table existence...")
            
            # Check if tables exist by trying to query them
            tables_to_check = [
                ('users', User),
                ('registered_users', RegisteredUser), 
                ('notifications', Notification)
            ]
            
            for table_name, model_class in tables_to_check:
                try:
                    count = db.session.query(model_class).count()
                    print(f"✅ {table_name} table exists with {count} records")
                except Exception as e:
                    print(f"❌ {table_name} table issue: {e}")
            
            print("\n3. Checking notification table schema...")
            
            # Use SQLAlchemy to inspect the actual table structure
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            if 'notifications' in inspector.get_table_names():
                columns = inspector.get_columns('notifications')
                foreign_keys = inspector.get_foreign_keys('notifications')
                
                print("Notification table columns:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
                
                print("Foreign key constraints:")
                for fk in foreign_keys:
                    print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                    if 'ondelete' in fk and fk['ondelete']:
                        print(f"    ON DELETE: {fk['ondelete']}")
                    else:
                        print("    ON DELETE: (not specified)")
            else:
                print("❌ Notifications table not found in database")
                
            return True
                
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            import traceback
            traceback.print_exc()
            return False

def create_test_notification():
    """Create a test notification to verify the setup"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n=== Creating Test Data ===")
            
            # Check if we have any users
            user_count = User.query.count()
            print(f"Current users in database: {user_count}")
            
            if user_count == 0:
                print("Creating a test user...")
                
                # Create test user
                test_user = User(
                    username='testuser',
                    email='test@example.com', 
                    password_hash='test_hash',
                    user_type='registered'
                )
                db.session.add(test_user)
                db.session.flush()
                
                # Create registered user profile
                reg_user = RegisteredUser(user_id=test_user.user_id)
                db.session.add(reg_user)
                db.session.flush()
                
                print(f"Created test user: {test_user.username}")
            else:
                # Use existing user
                test_user = User.query.first()
                reg_user = RegisteredUser.query.filter_by(user_id=test_user.user_id).first()
                
                if not reg_user:
                    # Create registered user profile if missing
                    reg_user = RegisteredUser(user_id=test_user.user_id)
                    db.session.add(reg_user)
                    db.session.flush()
                
                print(f"Using existing user: {test_user.username}")
            
            # Create test notification
            test_notification = Notification(
                message="Test notification - deletion fix verification",
                recipient_registered_user_id=reg_user.registered_user_id,
                action="test"
            )
            db.session.add(test_notification)
            db.session.commit()
            
            print(f"✅ Created test notification ID: {test_notification.notification_id}")
            
            # Verify we can query it
            notification_count = Notification.query.count()
            print(f"Total notifications in database: {notification_count}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating test data: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Database Setup Script")
    print("=" * 40)
    
    if setup_and_verify_database():
        print("\n" + "=" * 40)
        create_test_notification()
        print("\n🎉 Database setup completed successfully!")
        print("\nYou can now test the notification deletion fix.")
    else:
        print("\n❌ Database setup failed.")
