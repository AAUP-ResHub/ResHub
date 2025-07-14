import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Check if the table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workspace_documents'")
if cursor.fetchone() is None:
    print("Creating workspace_documents table...")
    
    # Create the workspace_documents table with the required schema
    cursor.execute('''
    CREATE TABLE workspace_documents (
        document_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(255) NOT NULL,
        content TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        workspace_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES collaboration_workspaces (workspace_id),
        FOREIGN KEY (creator_id) REFERENCES registered_users (registered_user_id)
    )
    ''')
    
    # Commit the changes
    conn.commit()
    print("Table created successfully.")
else:
    print("The workspace_documents table already exists.")
    
    # Check if document_id column exists
    try:
        cursor.execute("SELECT document_id FROM workspace_documents LIMIT 1")
        print("document_id column exists.")
    except sqlite3.OperationalError:
        print("document_id column doesn't exist, adding it...")
        
        # SQLite doesn't support adding a primary key column to an existing table directly
        # We need to create a new table, copy data, drop the old one, and rename the new one
        
        # Create new table with correct schema
        cursor.execute('''
        CREATE TABLE workspace_documents_new (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            content TEXT,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            workspace_id INTEGER NOT NULL,
            creator_id INTEGER NOT NULL,
            FOREIGN KEY (workspace_id) REFERENCES collaboration_workspaces (workspace_id),
            FOREIGN KEY (creator_id) REFERENCES registered_users (registered_user_id)
        )
        ''')
        
        # Copy data from old table to new table
        cursor.execute('''
        INSERT INTO workspace_documents_new (title, content, created_at, updated_at, workspace_id, creator_id)
        SELECT title, content, created_at, updated_at, workspace_id, creator_id FROM workspace_documents
        ''')
        
        # Drop old table
        cursor.execute("DROP TABLE workspace_documents")
        
        # Rename new table to original name
        cursor.execute("ALTER TABLE workspace_documents_new RENAME TO workspace_documents")
        
        # Commit changes
        conn.commit()
        print("Added document_id column successfully.")

# Close the connection
conn.close()
