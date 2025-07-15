from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from datetime import datetime, timedelta
import os

app = create_app()

with app.app_context():
    # Find the existing user
    user = User.query.filter_by(username='layan').first()
    
    if not user:
        print("Error: User 'layan' not found. Please run init_db.py first.")
        exit(1)
    
    print(f"Found user: {user.username} (ID: {user.user_id})")
    
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
                first_name="Layan",
                last_name="Researcher",
                affiliation="Research University"
            )
            # Try setting research interests attribute if it exists in the model
            if hasattr(RegisteredUser, 'research_interests'):
                registered_user.research_interests = "artificial intelligence, machine learning, natural language processing"
            db.session.add(registered_user)
            db.session.flush()
            print(f"Created RegisteredUser with ID: {registered_user.registered_user_id}")
        except Exception as e:
            print(f"Error creating RegisteredUser: {e}")
            # If research_interests causes the error, try without it
            try:
                registered_user = RegisteredUser(
                    user_id=user.user_id,
                    first_name="Layan",
                    last_name="Researcher",
                    affiliation="Research University"
                )
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
                    subscription_end_date=datetime.utcnow() + timedelta(days=365),
                    additional_quota=1000
                )
                # Try setting semantic_graph if it exists in the model
                if hasattr(PremiumUser, 'semantic_graph'):
                    premium_user.semantic_graph = {
                        "artificial intelligence": 1,
                        "machine learning": 1,
                        "natural language processing": 1
                    }
                db.session.add(premium_user)
                print("Created PremiumUser record")
            except Exception as e:
                print(f"Error creating PremiumUser: {e}")
                # Try without semantic_graph if that's causing the issue
                try:
                    premium_user = PremiumUser(
                        registered_user_id=registered_user.registered_user_id,
                        subscription_end_date=datetime.utcnow() + timedelta(days=365),
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
                    last_name=f"Researcher{i}",
                    affiliation=f"University {i}"
                )
                # Try setting research_interests if it exists
                if hasattr(RegisteredUser, 'research_interests'):
                    sample_registered.research_interests = interests_map[i]
                    
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
print("Username: layan")
print("Password: password123")
