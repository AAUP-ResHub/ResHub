from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os

# Create Flask app context
app = create_app()

# Get database path from config
with app.app_context():
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
    else:
        db_path = db_uri

print(f"Database path: {db_path}")

# Delete existing database file if it exists
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")
    except Exception as e:
        print(f"Error removing database: {e}")

# Create new database with all tables and test user
with app.app_context():
    # Create all tables
    db.create_all()
    print("Created fresh database schema")
    
    # Create premium user with complete hierarchy
    
    # 1. Create base User
    user = User(
        username="layan",
        email="layan@example.com",
        password_hash=generate_password_hash("password123"),
        user_type="premium"
    )
    db.session.add(user)
    db.session.flush()  # Get the user ID without committing
    
    # 2. Create RegisteredUser
    registered_user = RegisteredUser(
        user_id=user.user_id,
        first_name="Layan",
        last_name="Researcher",
        affiliation="Research University",
        research_interests="artificial intelligence, machine learning, natural language processing"
    )
    db.session.add(registered_user)
    db.session.flush()  # Get the registered_user ID
    
    # 3. Create PremiumUser
    premium_user = PremiumUser(
        registered_user_id=registered_user.registered_user_id,
        subscription_end_date=datetime.utcnow() + timedelta(days=365),
        additional_quota=1000,
        semantic_graph={
            "artificial intelligence": 1,
            "machine learning": 1,
            "natural language processing": 1
        }
    )
    db.session.add(premium_user)
    
    # Create some sample users with research interests for the semantic graph to work with
    for i in range(1, 6):
        # Create similar users with overlapping interests
        sample_user = User(
            username=f"researcher{i}",
            email=f"researcher{i}@example.com",
            password_hash=generate_password_hash("password123"),
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
            affiliation=f"University {i}",
            research_interests=interests_map[i]
        )
        db.session.add(sample_registered)
    
    # Commit all changes
    db.session.commit()
    print("✅ Database initialized successfully with premium user 'layan'")
    print("✅ Added 5 sample researchers with overlapping interests")
    print("\nCredentials for testing:")
    print("Username: layan")
    print("Password: password123")
    print("\nNow restart the Flask app to see the Semantic Graph!")
