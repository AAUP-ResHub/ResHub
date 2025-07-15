from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from datetime import datetime, timedelta
import sqlite3
import os

app = create_app()

# Get database path
with app.app_context():
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
    else:
        # For other database types
        db_path = db_uri

print(f"Database path: {db_path}")

# First check if the database exists
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
    print("Creating database and tables...")

# Add missing columns to registered_users table using raw SQL
def add_missing_columns():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if registered_users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='registered_users';")
        if cursor.fetchone() is None:
            print("Table registered_users doesn't exist. Will be created by SQLAlchemy.")
        else:
            # Check if research_interests column exists
            cursor.execute("PRAGMA table_info(registered_users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'research_interests' not in columns:
                print("Adding research_interests column to registered_users table")
                cursor.execute("ALTER TABLE registered_users ADD COLUMN research_interests TEXT")
            
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error modifying schema: {e}")

# Create or update complete user hierarchy
with app.app_context():
    # First make sure all tables exist
    db.create_all()
    
    # Add missing columns if needed
    add_missing_columns()
    
    # Get or create user
    user = User.query.filter_by(username='layan').first()
    if not user:
        print("Creating new user 'layan'...")
        from werkzeug.security import generate_password_hash
        user = User(
            username="layan",
            email="layan@example.com",
            password_hash=generate_password_hash("password123"),
            user_type="premium"
        )
        db.session.add(user)
        db.session.flush()
    else:
        print(f"Found existing user: {user.username}")
        # Ensure user_type is set to premium
        user.user_type = "premium"
    
    # Get or create RegisteredUser
    registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
    if not registered_user:
        print("Creating RegisteredUser record...")
        registered_user = RegisteredUser(
            user_id=user.user_id,
            first_name="Layan",
            last_name="Researcher",
            affiliation="Research University"
        )
        db.session.add(registered_user)
        db.session.flush()
    
    # Set research interests - add attribute check in case column doesn't exist
    try:
        registered_user.research_interests = "artificial intelligence, machine learning, natural language processing"
        print("Added research interests to user profile")
    except Exception as e:
        print(f"Warning: Couldn't set research_interests: {e}")
    
    # Get or create PremiumUser
    premium_user = None
    try:
        premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
    except Exception as e:
        print(f"Error querying PremiumUser: {e}")
    
    if not premium_user:
        try:
            print("Creating PremiumUser record...")
            premium_user = PremiumUser(
                registered_user_id=registered_user.registered_user_id,
                subscription_end_date=datetime.utcnow() + timedelta(days=365),
                additional_quota=1000
            )
            db.session.add(premium_user)
        except Exception as e:
            print(f"Error creating PremiumUser: {e}")
    
    # Set semantic graph if possible
    try:
        if premium_user:
            premium_user.semantic_graph = {
                "artificial intelligence": 1,
                "machine learning": 1,
                "natural language processing": 1
            }
            print("Added semantic graph data")
    except Exception as e:
        print(f"Warning: Couldn't set semantic_graph: {e}")
    
    # Commit all changes
    try:
        db.session.commit()
        print("✅ Database updates committed successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error committing changes: {e}")

# Display final database structure
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nFinal database structure:")
    
    # For each table, get its structure
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print(f"\nTable: {table_name}")
        for col in columns:
            # col format: (id, name, type, notnull, default_value, primary_key)
            print(f"  {col[1]} ({col[2]})")
    
    conn.close()
except Exception as e:
    print(f"Error reading database structure: {e}")

print("\nNow restart your Flask application to see the Semantic Graph!")
