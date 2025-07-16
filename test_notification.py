from app import create_app, db
from app.models import User, RegisteredUser, Notification
from app.services.notification_service import send_notification
from werkzeug.security import generate_password_hash

# Create a Flask application context for testing
app = create_app()

def create_test_user(username, email):
    """Create a test user if needed"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # Get the corresponding registered user
            registered_user = RegisteredUser.query.filter_by(user_id=existing_user.user_id).first()
            return registered_user
        
        # Create a new user
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash("testpassword"),
            user_type='registered'
        )
        db.session.add(user)
        db.session.commit()
        
        # Create a registered user profile
        registered_user = RegisteredUser(
            user_id=user.user_id,
            first_name=f"Test {username}",
            last_name="User"
        )
        db.session.add(registered_user)
        db.session.commit()
        
        print(f"Created test user: {username} with registered_user_id: {registered_user.registered_user_id}")
        return registered_user

def test_notification_with_actor():
    with app.app_context():
        print("Starting notification test...")
        
        # Create or get test users
        recipient = create_test_user("testrecipient", "recipient@test.com")
        actor = create_test_user("testactor", "actor@test.com")
        
        if recipient and actor:
            print(f"Using recipient: {recipient.registered_user_id} and actor: {actor.registered_user_id}")
            
            # Create a notification using the service
            notification = send_notification(
                recipient_user=recipient,
                actor_user=actor,
                action_key="test_action",
                context_data={"test": "data"}
            )
            
            # Verify the notification was created
            if notification:
                print(f"Notification created: {notification.notification_id}")
                print(f"- Message: {notification.message}")
                print(f"- Action: {notification.action}")
                print(f"- Recipient ID: {notification.recipient_registered_user_id}")
                print(f"- Actor ID: {notification.actor_registered_user_id}")
                
                # Verify the relationship works
                if notification.actor:
                    print(f"- Actor Username: {notification.actor.user.username}")
                else:
                    print("Actor relationship not working properly")
                
                # Check the reverse relationship too
                actor_notifications = actor.triggered_notifications.all()
                if actor_notifications:
                    print(f"Actor triggered {len(actor_notifications)} notifications")
                else:
                    print("No notifications found via actor's triggered_notifications")
                
                return True
            else:
                print("Failed to create notification")
                return False
        else:
            print("Could not create test users")
            return False

if __name__ == "__main__":
    success = test_notification_with_actor()
    print(f"Test {'succeeded' if success else 'failed'}")