from app import create_app
import sqlite3
import os

app = create_app()

# Get database path from app config
with app.app_context():
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

# If it's a relative path, make it absolute
if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(__file__), db_path)

print(f"Database path: {db_path}")

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(f"- {table[0]}")

# For each table, get its structure
print("\nTable structures:")
for table in tables:
    table_name = table[0]
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print(f"\nTable: {table_name}")
    for col in columns:
        # col format: (id, name, type, notnull, default_value, primary_key)
        print(f"  {col[1]} ({col[2]})")

conn.close()
