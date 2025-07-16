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

# First, fix the workspace_documents table by adding the is_default column
try:
    conn.execute('ALTER TABLE workspace_documents ADD COLUMN is_default BOOLEAN DEFAULT 0')
    print("Added is_default column to workspace_documents table")
    conn.commit()
except sqlite3.OperationalError as e:
    print(f"is_default column: {e}")

# Add columns to notifications table
try:
    # Try to add each column separately - some may already exist
    try:
        conn.execute('ALTER TABLE notifications ADD COLUMN action VARCHAR(255) NOT NULL DEFAULT "system"')
        print("Added action column")
    except sqlite3.OperationalError as e:
        print(f"Action column: {e}")

    try:
        conn.execute('ALTER TABLE notifications ADD COLUMN object_type VARCHAR(50)')
        print("Added object_type column")
    except sqlite3.OperationalError as e:
        print(f"object_type column: {e}")

    try:
        conn.execute('ALTER TABLE notifications ADD COLUMN object_id INTEGER')
        print("Added object_id column")
    except sqlite3.OperationalError as e:
        print(f"object_id column: {e}")

    try:
        conn.execute('ALTER TABLE notifications ADD COLUMN actor_registered_user_id INTEGER REFERENCES registered_users(registered_user_id)')
        print("Added actor_registered_user_id column")
    except sqlite3.OperationalError as e:
        print(f"actor_registered_user_id column: {e}")

    # Create indexes
    try:
        conn.execute('CREATE INDEX ix_notifications_actor_registered_user_id ON notifications (actor_registered_user_id)')
        print("Created index on actor_registered_user_id")
    except sqlite3.OperationalError as e:
        print(f"Index on actor_registered_user_id: {e}")

    try:
        conn.execute('CREATE INDEX ix_notifications_is_read ON notifications (is_read)')
        print("Created index on is_read")
    except sqlite3.OperationalError as e:
        print(f"Index on is_read: {e}")

    try:
        conn.execute('CREATE INDEX ix_notifications_recipient_registered_user_id ON notifications (recipient_registered_user_id)')
        print("Created index on recipient_registered_user_id")
    except sqlite3.OperationalError as e:
        print(f"Index on recipient_registered_user_id: {e}")

    try:
        conn.execute('CREATE INDEX ix_notifications_sent_date ON notifications (sent_date)')
        print("Created index on sent_date")
    except sqlite3.OperationalError as e:
        print(f"Index on sent_date: {e}")

    # Commit all changes
    conn.commit()
    print("Successfully updated the notifications table")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()