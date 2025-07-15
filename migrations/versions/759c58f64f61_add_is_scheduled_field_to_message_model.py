"""Add is_scheduled field to Message model

Revision ID: 759c58f64f61
Revises: 6c329e03af7d
Create Date: 2023-07-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '759c58f64f61'
down_revision = '6c329e03af7d'
branch_labels = None
depends_on = None


def upgrade():
    # This is just a placeholder to maintain revision history
    pass


def downgrade():
    # This is just a placeholder to maintain revision history
    pass
