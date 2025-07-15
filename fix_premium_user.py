from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Find our user named 'layan'
    user = User.query.filter_by(username='layan').first()
    
    if not user:
        print("Error: User 'layan' not found. Run init_db.py first.")
    else:
        # Check if RegisteredUser already exists
        registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
        
        if not registered_user:
            # Create RegisteredUser
            registered_user = RegisteredUser(
                user_id=user.user_id,
                first_name="Layan",
                last_name="Researcher",
                affiliation="Research University",
                research_interests="artificial intelligence, machine learning, natural language processing"
            )
            db.session.add(registered_user)
            db.session.flush()  # Get the ID without committing
            print(f"Created RegisteredUser for {user.username}")
        else:
            # Update research interests if the record exists
            registered_user.research_interests = "artificial intelligence, machine learning, natural language processing"
            print(f"Updated RegisteredUser for {user.username}")
            
        # Check if PremiumUser already exists
        premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
        
        if not premium_user:
            # Create PremiumUser with semantic graph data
            one_year_later = datetime.utcnow() + timedelta(days=365)
            
            premium_user = PremiumUser(
                registered_user_id=registered_user.registered_user_id,
                subscription_end_date=one_year_later,
                additional_quota=1000,
                semantic_graph={
                    "artificial intelligence": 1,
                    "machine learning": 1,
                    "natural language processing": 1
                }
            )
            db.session.add(premium_user)
            print(f"Created PremiumUser for {user.username}")
        else:
            # Update semantic graph if the record exists
            premium_user.semantic_graph = {
                "artificial intelligence": 1,
                "machine learning": 1,
                "natural language processing": 1
            }
            print(f"Updated PremiumUser for {user.username}")
            
        db.session.commit()
        print("✅ Premium user setup complete with research interests")
