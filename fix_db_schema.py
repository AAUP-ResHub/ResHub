from app import create_app
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
        db_path = db_uri

print(f"Database path: {db_path}")

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if the database exists and has tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [table[0] for table in cursor.fetchall()]
print(f"Found tables: {tables}")

# 1. Add missing research_interests column to registered_users if it exists
if 'registered_users' in tables:
    # Check if column exists
    cursor.execute("PRAGMA table_info(registered_users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'research_interests' not in columns:
        print("Adding research_interests column to registered_users table...")
        try:
            cursor.execute("ALTER TABLE registered_users ADD COLUMN research_interests TEXT")
            print("Successfully added research_interests column.")
        except Exception as e:
            print(f"Failed to add research_interests column: {e}")

# 2. Add semantic_graph column to premium_users if it exists
if 'premium_users' in tables:
    # Check if column exists
    cursor.execute("PRAGMA table_info(premium_users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'semantic_graph' not in columns:
        print("Adding semantic_graph column to premium_users table...")
        try:
            cursor.execute("ALTER TABLE premium_users ADD COLUMN semantic_graph TEXT")
            print("Successfully added semantic_graph column.")
        except Exception as e:
            print(f"Failed to add semantic_graph column: {e}")

# Add sample data for our premium user
print("\nUpdating user data...")

# Update the layan user to premium type
cursor.execute("UPDATE users SET user_type = 'premium' WHERE username = 'layan'")
print(f"Updated {cursor.rowcount} users to premium")

# Create or update RegisteredUser record for layan
cursor.execute("SELECT user_id FROM users WHERE username = 'layan'")
user_id_result = cursor.fetchone()
if user_id_result:
    user_id = user_id_result[0]
    
    # Check if registered user exists
    cursor.execute("SELECT registered_user_id FROM registered_users WHERE user_id = ?", (user_id,))
    registered_user_result = cursor.fetchone()
    
    if registered_user_result:
        registered_user_id = registered_user_result[0]
        print(f"Found existing RegisteredUser (ID: {registered_user_id})")
        
        # Update research interests
        cursor.execute(
            "UPDATE registered_users SET research_interests = ? WHERE registered_user_id = ?", 
            ("artificial intelligence, machine learning, natural language processing", registered_user_id)
        )
        print(f"Updated {cursor.rowcount} registered users with research interests")
    else:
        # Create new RegisteredUser
        cursor.execute(
            "INSERT INTO registered_users (user_id, first_name, last_name, research_interests, affiliation) VALUES (?, ?, ?, ?, ?)", 
            (user_id, "Layan", "Researcher", "artificial intelligence, machine learning, natural language processing", "Research University")
        )
        print("Created new RegisteredUser record")
        
        # Get the new registered_user_id
        cursor.execute("SELECT last_insert_rowid()")
        registered_user_id = cursor.fetchone()[0]
    
    # Check if premium user exists
    cursor.execute("SELECT premium_user_id FROM premium_users WHERE registered_user_id = ?", (registered_user_id,))
    premium_user_result = cursor.fetchone()
    
    if premium_user_result:
        premium_user_id = premium_user_result[0]
        print(f"Found existing PremiumUser (ID: {premium_user_id})")
        
        # Update semantic graph
        cursor.execute(
            "UPDATE premium_users SET semantic_graph = ? WHERE premium_user_id = ?", 
            ('{"artificial intelligence": 1, "machine learning": 1, "natural language processing": 1}', premium_user_id)
        )
        print(f"Updated {cursor.rowcount} premium users with semantic graph data")
    else:
        # Create new PremiumUser
        cursor.execute(
            "INSERT INTO premium_users (registered_user_id, subscription_end_date, additional_quota, semantic_graph) VALUES (?, date('now', '+1 year'), 1000, ?)", 
            (registered_user_id, '{"artificial intelligence": 1, "machine learning": 1, "natural language processing": 1}')
        )
        print("Created new PremiumUser record")

# Create sample researchers for the semantic graph
for i in range(1, 6):
    # Check if user exists
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (f"researcher{i}",))
    researcher_exists = cursor.fetchone()
    
    if not researcher_exists:
        # Create sample user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, user_type) VALUES (?, ?, ?, ?)", 
            (f"researcher{i}", f"researcher{i}@example.com", "pbkdf2:sha256:600000$somepasswordhash", "registered")
        )
        
        # Get the new user_id
        cursor.execute("SELECT last_insert_rowid()")
        user_id = cursor.fetchone()[0]
        
        # Different overlapping research interests for each sample user
        interests_map = {
            1: "artificial intelligence, computer vision, robotics",
            2: "machine learning, deep learning, neural networks",
            3: "natural language processing, computational linguistics",
            4: "artificial intelligence, data mining, knowledge graphs",
            5: "machine learning, natural language processing, chatbots"
        }
        
        # Create RegisteredUser
        cursor.execute(
            "INSERT INTO registered_users (user_id, first_name, last_name, affiliation, research_interests) VALUES (?, ?, ?, ?, ?)", 
            (user_id, f"Sample{i}", f"Researcher{i}", f"University {i}", interests_map[i])
        )
        
        print(f"Created sample researcher {i}")

# Commit changes and close connection
conn.commit()
conn.close()

print("\n✅ Database schema and user data updated successfully!")
print("Please restart your Flask application to see the Semantic Graph section.")
print("\nLogin credentials:")
print("Username: layan")
print("Password: password123")
