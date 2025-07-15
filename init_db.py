from app import create_app
from app.extensions import db
from app.models import User, RegisteredUser, PremiumUser
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import sqlite3

def init_db():
    app = create_app()
    
    print('[INFO] Starting database initialization...')
    
    # Display database path
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        else:
            db_path = db_uri
        print(f'[INFO] Database path: {db_path}')
        
        # Check if database file exists
        if os.path.exists(db_path):
            file_size = os.path.getsize(db_path)
            print(f'[INFO] Database file exists, size: {file_size} bytes')
            if file_size > 0:
                print('[INFO] Checking existing database structure...')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f'[INFO] Existing tables: {[t[0] for t in tables]}')
                conn.close()
        else:
            print('[INFO] Database file does not exist, will be created')

        # Initialize database
        print('[INFO] Creating database schema...')
        db.drop_all()  # Drop all tables first for a clean start
        db.create_all()  # Create all tables based on the models
        
        # Check if schema was created properly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'[INFO] Created tables: {[t[0] for t in tables]}')
        
        # Check columns in key tables
        if 'users' in [t[0] for t in tables]:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            print(f'[INFO] users table columns: {[c[1] for c in columns]}')
        
        if 'registered_users' in [t[0] for t in tables]:
            cursor.execute("PRAGMA table_info(registered_users)")
            columns = cursor.fetchall()
            print(f'[INFO] registered_users table columns: {[c[1] for c in columns]}')
            
        if 'premium_users' in [t[0] for t in tables]:
            cursor.execute("PRAGMA table_info(premium_users)")
            columns = cursor.fetchall()
            print(f'[INFO] premium_users table columns: {[c[1] for c in columns]}')
        
        conn.close()
        
        # Create the premium user with complete hierarchy
        print('[INFO] Creating premium user...')
        
        # 1. Create base User
        user = User(
            username='layan',
            email='layan@example.com',
            password_hash=generate_password_hash('password123'),
            user_type='premium'
        )
        db.session.add(user)
        db.session.flush()  # Get user_id without committing
        print(f'[INFO] Created User with ID: {user.user_id}')
        
        # 2. Create RegisteredUser
        registered_user = RegisteredUser(
            user_id=user.user_id,
            first_name='Layan',
            last_name='Researcher',
            affiliation='Research University',
            research_interests='artificial intelligence, machine learning, natural language processing'
        )
        db.session.add(registered_user)
        db.session.flush()
        print(f'[INFO] Created RegisteredUser with ID: {registered_user.registered_user_id}')
        
        # 3. Create PremiumUser
        premium_user = PremiumUser(
            registered_user_id=registered_user.registered_user_id,
            premium_since=datetime.utcnow(),
            additional_quota=1000,
            semantic_graph={
                "artificial intelligence": 1,
                "machine learning": 1,
                "natural language processing": 1
            }
        )
        db.session.add(premium_user)
        print('[INFO] Created PremiumUser record')
        
        # Create sample researchers for the semantic graph visualization
        print('[INFO] Creating sample researchers...')
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
            print(f'[INFO] Created researcher{i}')
        
        # Commit all changes
        db.session.commit()
        print('[OK] All database changes committed successfully!')
    
    print('[SUCCESS] Database initialized with premium user "layan" and sample researchers')
    print('[INFO] You can now run the application with "python app.py" and login with:')
    print('Username: layan')
    print('Password: password123')

if __name__ == '__main__':
    init_db()
