from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from datetime import datetime, timedelta
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
        from werkzeug.security import generate_password_hash
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
    registered_user = None
    try:
        # First check if it exists
        registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
    except Exception as e:
        print(f"Error checking for RegisteredUser: {e}")
    
    if registered_user:
        print(f"Found existing RegisteredUser record (ID: {registered_user.registered_user_id})")
    else:
        print("Creating new RegisteredUser record...")
        try:
            registered_user = RegisteredUser(
                user_id=user.user_id,
                first_name="Khalid",
                last_name="Researcher"
            )
            # Set profile_data with research info since affiliation/research_interests don't exist
            registered_user.profile_data = "Affiliation: Research University | Research Interests: artificial intelligence, machine learning, natural language processing"
            db.session.add(registered_user)
            db.session.flush()
            print(f"Created RegisteredUser with ID: {registered_user.registered_user_id}")
        except Exception as e:
            print(f"Error creating RegisteredUser: {e}")
            # If research_interests causes the error, try without it
            try:
                registered_user = RegisteredUser(
                    user_id=user.user_id,
                    first_name="Khalid",
                    last_name="Researcher"
                )
                registered_user.profile_data = "Affiliation: Research University | Research Interests: artificial intelligence, machine learning, natural language processing"
                db.session.add(registered_user)
                db.session.flush()
                print(f"Created RegisteredUser (without research_interests) with ID: {registered_user.registered_user_id}")
            except Exception as e2:
                print(f"Still couldn't create RegisteredUser: {e2}")
                exit(1)
    
    # Make sure user_type is set to premium
    user.user_type = 'premium'
    
    # Get or create the PremiumUser record
    premium_user = None
    if registered_user:
        try:
            premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
        except Exception as e:
            print(f"Error checking for PremiumUser: {e}")
        
        if premium_user:
            print(f"Found existing PremiumUser record (ID: {premium_user.premium_user_id})")
        else:
            print("Creating new PremiumUser record...")
            try:
                premium_user = PremiumUser(
                    registered_user_id=registered_user.registered_user_id,
                    additional_quota=1000
                )
                # Note: Current schema doesn't have subscription_end_date or semantic_graph fields
                db.session.add(premium_user)
                print("Created PremiumUser record")
            except Exception as e:
                print(f"Error creating PremiumUser: {e}")
                # Try without semantic_graph if that's causing the issue
                try:
                    premium_user = PremiumUser(
                        registered_user_id=registered_user.registered_user_id,
                        additional_quota=1000
                    )
                    db.session.add(premium_user)
                    print("Created PremiumUser record (without semantic_graph)")
                except Exception as e2:
                    print(f"Still couldn't create PremiumUser: {e2}")
    
    # Create sample users with research interests for the semantic graph
    try:
        # Only create sample users if they don't exist
        if User.query.filter_by(username='researcher1').first() is None:
            print("Creating sample researchers for the semantic graph...")
            for i in range(1, 6):
                sample_user = User(
                    username=f"researcher{i}",
                    email=f"researcher{i}@example.com",
                    password_hash=user.password_hash,  # Use same hash for simplicity
                    user_type="registered"
                )
                db.session.add(sample_user)
                db.session.flush()
                
                # Different overlapping research interests for each sample user
                interests_map = {
                    1: "artificial intelligence, computer vision, robotics",
                    2: "machine learning, deep learning, neural networks",
                    3: "natural language processing, computational linguistics",
                    4: "artificial intelligence, data mining, knowledge graphs",
                    5: "machine learning, natural language processing, chatbots"
                }
                
                sample_registered = RegisteredUser(
                    user_id=sample_user.user_id,
                    first_name=f"Sample{i}",
                    last_name=f"Researcher{i}"
                )
                # Store research info in profile_data since specific fields don't exist
                sample_registered.profile_data = f"Affiliation: University {i} | Research Interests: {interests_map[i]}"
                    
                db.session.add(sample_registered)
                print(f"Created researcher{i}")
        else:
            print("Sample researchers already exist, skipping creation")
    except Exception as e:
        print(f"Error creating sample researchers: {e}")
    
    # Save all changes
    try:
        db.session.commit()
        print("\n✅ Successfully updated the user profile")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving changes: {e}")
        exit(1)

print("\nNow restart your Flask application to see the Semantic Graph section!")
print("Username: khalid")
print("Password: password123")
