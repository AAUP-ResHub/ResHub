from app import create_app, db
from app.models import User, RegisteredUser, Notification
from datetime import datetime

# Create a Flask application context
app = create_app()

def verify_notification_model():
    with app.app_context():
        print("Starting notification model verification...")
        
        # 1. Verify table structure
        print("Checking database schema for notifications table...")
        
        # Get column names from the Notification model
        column_names = [column.name for column in Notification.__table__.columns]
        print(f"Columns in Notification model: {column_names}")
        
        # Check that our new columns exist
        required_columns = ['actor_registered_user_id', 'action', 'object_type', 'object_id']
        for col in required_columns:
            if col in column_names:
                print(f"✓ Column '{col}' exists in the model")
            else:
                print(f"❌ Column '{col}' is missing from the model")
        
        # 2. Find test users or create them if needed
        recipient = RegisteredUser.query.first()
        if not recipient:
            print("Creating a test recipient...")
            user = User(username="test_recipient", email="test_recipient@example.com", 
                      password_hash="test_hash", user_type="registered")
            db.session.add(user)
            db.session.flush()
            
            recipient = RegisteredUser(user_id=user.user_id, first_name="Test", last_name="Recipient")
            db.session.add(recipient)
            db.session.commit()
        
        actor = None
        if RegisteredUser.query.count() > 1:
            # Find a different user for actor
            actor = RegisteredUser.query.filter(RegisteredUser.registered_user_id != recipient.registered_user_id).first()
        
        if not actor:
            print("Creating a test actor...")
            user = User(username="test_actor", email="test_actor@example.com", 
                      password_hash="test_hash", user_type="registered")
            db.session.add(user)
            db.session.flush()
            
            actor = RegisteredUser(user_id=user.user_id, first_name="Test", last_name="Actor")
            db.session.add(actor)
            db.session.commit()
        
        # 3. Create a notification directly using the model (bypass service)
        print(f"\nCreating test notification with recipient ID: {recipient.registered_user_id} and actor ID: {actor.registered_user_id}")
        notification = Notification(
            message="This is a direct test notification",
            recipient_registered_user_id=recipient.registered_user_id,
            actor_registered_user_id=actor.registered_user_id,
            action="test_direct",
            object_type="test",
            object_id=1,
            sent_date=datetime.utcnow(),
            is_read=False
        )
        
        try:
            db.session.add(notification)
            db.session.commit()
            print(f"✓ Successfully created notification with ID: {notification.notification_id}")
            
            # Verify notification was saved correctly
            saved_notification = Notification.query.get(notification.notification_id)
            print(f"Notification details:")
            print(f"  - Message: {saved_notification.message}")
            print(f"  - Action: {saved_notification.action}")
            print(f"  - Actor ID: {saved_notification.actor_registered_user_id}")
            print(f"  - Recipient ID: {saved_notification.recipient_registered_user_id}")
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to create notification: {e}")
            return False

if __name__ == "__main__":
    success = verify_notification_model()
    print(f"\nVerification {'succeeded' if success else 'failed'}")