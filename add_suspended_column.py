from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Add the is_suspended column to the users table
    db.session.execute(text('ALTER TABLE users ADD COLUMN is_suspended BOOLEAN DEFAULT 0 NOT NULL'))
    db.session.commit()
    print("Successfully added is_suspended column to users table")
