"""Removed all schedule message logic

Revision ID: d45f62a9123c
Revises: 759c58f64f61
Create Date: 2025-07-12 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd45f62a9123c'
down_revision = '759c58f64f61'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite can only execute one statement at a time
    # 1. Turn off foreign keys
    op.execute('PRAGMA foreign_keys=off')
    
    # 2. Create a temporary table without the is_scheduled column
    op.execute(
        'CREATE TABLE messages_temp (\n'
        '    message_id INTEGER PRIMARY KEY,\n'
        '    sender_id INTEGER NOT NULL,\n'
        '    receiver_id INTEGER NOT NULL,\n'
        '    content TEXT NOT NULL,\n'
        '    timestamp DATETIME NOT NULL,\n'
        '    is_read BOOLEAN,\n'
        '    parent_id INTEGER,\n'
        '    FOREIGN KEY (sender_id) REFERENCES users (user_id),\n'
        '    FOREIGN KEY (receiver_id) REFERENCES users (user_id),\n'
        '    FOREIGN KEY (parent_id) REFERENCES messages (message_id)\n'
        ')')
    
    # 3. Copy data from the original table to the temporary table
    op.execute(
        'INSERT INTO messages_temp '
        'SELECT message_id, sender_id, receiver_id, content, timestamp, is_read, parent_id '
        'FROM messages')
    
    # 4. Drop the original table
    op.execute('DROP TABLE messages')
    
    # 5. Rename the temporary table to the original name
    op.execute('ALTER TABLE messages_temp RENAME TO messages')
    
    # 6. Turn on foreign keys
    op.execute('PRAGMA foreign_keys=on')


def downgrade():
    # We don't need to add the column back in downgrade since we're removing the feature
    pass
