import sqlite3
import os

# Identify the database file
db_paths = ['instance/app.db', 'app.db', 'app/app.db', 'data/app.db']
db_file = None

for path in db_paths:
    if os.path.exists(path):
        db_file = path
        break

if not db_file:
    print("Database file not found! Please provide the correct path.")
    exit(1)

print(f"Using database at: {db_file}")

# Connect to the database
conn = sqlite3.connect(db_file)

# Add document_id column to workspace_files table
try:
    # Add the document_id column
    conn.execute('ALTER TABLE workspace_files ADD COLUMN document_id INTEGER REFERENCES workspace_documents(id)')
    print("Added document_id column to workspace_files table")
    
    # Create index for the document_id column
    conn.execute('CREATE INDEX ix_workspace_files_document_id ON workspace_files(document_id)')
    print("Created index for document_id column")
    
    # Commit the changes
    conn.commit()
    print("Migration successfully applied!")
except sqlite3.OperationalError as e:
    print(f"Error: {e}")
finally:
    conn.close()
