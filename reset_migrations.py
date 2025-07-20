import sqlite3
import os
import shutil

# Connect to the database
conn = sqlite3.connect('instance/app.db')
cursor = conn.cursor()

try:
    # Check if alembic_version table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    if cursor.fetchone():
        # Drop the alembic_version table to reset migration tracking
        cursor.execute("DROP TABLE alembic_version")
        print("Successfully dropped alembic_version table")
    else:
        print("No alembic_version table found")
    
    conn.commit()
    print("Database migration history cleared")
    
    # Backup migrations directory
    if os.path.exists('migrations'):
        if os.path.exists('migrations_backup'):
            shutil.rmtree('migrations_backup')
        shutil.move('migrations', 'migrations_backup')
        print("Backed up existing migrations folder to migrations_backup")
    
    print("\nNext steps:")
    print("1. Run 'python -m flask db init' to initialize a new migration repository")
    print("2. Run 'python -m flask db migrate -m \"Initial migration\"' to create the initial migration")
    print("3. Run 'python -m flask db upgrade' to apply the migration")
    
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
finally:
    conn.close()
