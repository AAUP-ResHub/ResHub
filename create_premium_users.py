from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import json
import os

app = create_app()

def create_premium_user(username, first_name, last_name, research_interests):
    """Create or upgrade a user to premium status"""
    print(f"\n=== Processing user: {username} ===")
    
    # Check if user already exists
    user = User.query.filter_by(username=username).first()
    
    if not user:
        print(f"Creating new user: {username}")
        # Create new user
        user = User(
            username=username,
            email=f"{username}@example.com",
            password_hash=generate_password_hash("password123"),
            user_type="premium"
        )
        db.session.add(user)
        db.session.flush()
        print(f"Created user: {username} (ID: {user.user_id})")
    else:
        print(f"Found existing user: {username} (ID: {user.user_id})")
        # Upgrade to premium if not already
        if user.user_type != "premium":
            user.user_type = "premium"
            print(f"Upgraded {username} to premium user type")
    
    # Get or create the RegisteredUser record
    registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
    
    if registered_user:
        print(f"Found existing RegisteredUser record (ID: {registered_user.registered_user_id})")
    else:
        print("Creating new RegisteredUser record...")
        registered_user = RegisteredUser(
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name
        )
        # Store research interests in profile_data as JSON
        profile_data = {
            "research_interests": research_interests,
            "affiliation": f"{first_name} Research Institute"
        }
        registered_user.profile_data = json.dumps(profile_data)
        db.session.add(registered_user)
        db.session.flush()
        print(f"Created RegisteredUser with ID: {registered_user.registered_user_id}")
    
    # Update research interests if user already exists
    if registered_user.profile_data:
        try:
            profile_data = json.loads(registered_user.profile_data)
        except:
            profile_data = {}
    else:
        profile_data = {}
    
    profile_data["research_interests"] = research_interests
    profile_data["affiliation"] = f"{first_name} Research Institute"
    registered_user.profile_data = json.dumps(profile_data)
    
    # Get or create the PremiumUser record
    premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
    
    if premium_user:
        print(f"Found existing PremiumUser record (ID: {premium_user.premium_user_id})")
    else:
        print("Creating new PremiumUser record...")
        premium_user = PremiumUser(
            registered_user_id=registered_user.registered_user_id,
            additional_quota=1000
        )
        db.session.add(premium_user)
        print("Created PremiumUser record")
    
    return user, registered_user, premium_user

def main():
    """Main function to create multiple premium users"""
    print("=== Creating Multiple Premium Users for Semantic Graph Testing ===")
    
    # Define the 3 premium users with overlapping research interests
    users_to_create = [
        {
            "username": "alice_researcher",
            "first_name": "Alice",
            "last_name": "Johnson",
            "research_interests": "artificial intelligence, machine learning, computer vision"
        },
        {
            "username": "bob_researcher", 
            "first_name": "Bob",
            "last_name": "Smith",
            "research_interests": "machine learning, natural language processing, deep learning"
        },
        {
            "username": "charlie_researcher",
            "first_name": "Charlie",
            "last_name": "Brown", 
            "research_interests": "natural language processing, artificial intelligence, chatbots"
        }
    ]
    
    created_users = []
    
    with app.app_context():
        try:
            for user_data in users_to_create:
                user, registered_user, premium_user = create_premium_user(
                    user_data["username"],
                    user_data["first_name"], 
                    user_data["last_name"],
                    user_data["research_interests"]
                )
                created_users.append({
                    "username": user_data["username"],
                    "user_id": user.user_id,
                    "registered_user_id": registered_user.registered_user_id,
                    "research_interests": user_data["research_interests"]
                })
            
            # Save all changes
            db.session.commit()
            print("\n✅ Successfully created all premium users!")
            
            # Print summary
            print("\n=== CREATED PREMIUM USERS ===")
            for user_info in created_users:
                print(f"Username: {user_info['username']}")
                print(f"Password: password123")
                print(f"Research: {user_info['research_interests']}")
                print("-" * 50)
            
            print("\n🔬 These users have overlapping research interests:")
            print("• Alice & Bob: machine learning")
            print("• Bob & Charlie: natural language processing") 
            print("• Alice & Charlie: artificial intelligence")
            print("\n👥 They should appear in each other's semantic graphs!")
            print("\nTest by logging in as any of these users and visiting their Profile page.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error creating users: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
