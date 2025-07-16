import sqlite3
import os

# Search for SQLite database files in the project directory
def find_sqlite_db():
    # Common database file patterns
    possible_db_names = ['app.db', 'instance/app.db', 'data.db', 'instance/data.db', 'site.db', 'instance/site.db']
    # Search in common locations
    for db_name in possible_db_names:
        if os.path.exists(db_name):
            return db_name
    # Check for database in 'instance' directory
    instance_dir = os.path.join(os.getcwd(), 'instance')
    if os.path.exists(instance_dir):
        for file in os.listdir(instance_dir):
            if file.endswith('.db'):
                return os.path.join('instance', file)
    return None

# Get the path to the database file
db_path = find_sqlite_db()

if not db_path:
    print("Could not find the SQLite database file. Please provide the path manually.")
    exit(1)

print(f"Using database: {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables to verify workspace_documents exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Available tables:")
for table in tables:
    print(f" - {table[0]}")

# Check if the workspace_documents table exists
workspace_documents_exists = any(table[0] == 'workspace_documents' for table in tables)

if not workspace_documents_exists:
    print("Error: workspace_documents table doesn't exist!")
    conn.close()
    exit(1)

# Check if the column exists already
cursor.execute("PRAGMA table_info(workspace_documents)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]
print("\nExisting columns in workspace_documents:")
for name in column_names:
    print(f" - {name}")

# Only add the column if it doesn't exist
if 'is_default' not in column_names:
    try:
        # Add the is_default column
        cursor.execute("ALTER TABLE workspace_documents ADD COLUMN is_default BOOLEAN DEFAULT 0")
        print("\nColumn 'is_default' added successfully!")
        conn.commit()
    except Exception as e:
        print(f"\nError adding column: {e}")
        conn.rollback()
else:
    print("\nColumn 'is_default' already exists.")

# Close the connection
conn.close()
