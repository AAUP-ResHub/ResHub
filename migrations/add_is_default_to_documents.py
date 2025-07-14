"""Add is_default column to workspace_documents

Revision ID: add_is_default_to_workspace_documents
Revises: ae2248bfc2e5
Create Date: 2025-06-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_is_default_to_workspace_documents'
down_revision = 'ae2248bfc2e5'  # ID from the latest migration we found (add_workspacedocument_model)
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workspace_documents', sa.Column('is_default', sa.Boolean(), nullable=True, server_default='0'))


def downgrade():
    op.drop_column('workspace_documents', 'is_default')
