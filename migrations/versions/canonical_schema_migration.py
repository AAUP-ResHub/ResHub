"""Canonical schema migration for ResHub

Revision ID: canonical_schema_001
Revises: 
Create Date: 2025-07-16 22:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import enum

# revision identifiers, used by Alembic.
revision = 'canonical_schema_001'
down_revision = None
branch_labels = None
depends_on = None


class CitationStyle(enum.Enum):
    APA = "APA"
    MLA = "MLA"
    IEEE = "IEEE"


def upgrade():
    # --- User Hierarchy ---
    op.create_table('users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('user_type', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    op.create_table('admins',
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('admin_id'),
        sa.UniqueConstraint('user_id')
    )

    op.create_table('registered_users',
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('profile_data', sa.Text(), nullable=True),
        sa.Column('research_stats', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('registered_user_id'),
        sa.UniqueConstraint('user_id')
    )

    op.create_table('premium_users',
        sa.Column('premium_user_id', sa.Integer(), nullable=False),
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('premium_since', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('additional_quota', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['registered_user_id'], ['registered_users.registered_user_id'], ),
        sa.PrimaryKeyConstraint('premium_user_id'),
        sa.UniqueConstraint('registered_user_id')
    )

    # --- Content and Interaction Entities ---
    op.create_table('research_papers',
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('publish_date', sa.DateTime(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('update_date', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('keywords', sa.String(length=255), nullable=True),
        sa.Column('doi', sa.String(length=100), nullable=True),
        sa.Column('owner_registered_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['owner_registered_user_id'], ['registered_users.registered_user_id'], ),
        sa.PrimaryKeyConstraint('paper_id')
    )

    op.create_table('paper_metrics',
        sa.Column('metric_id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('read_count', sa.Integer(), nullable=True, default=0),
        sa.Column('download_count', sa.Integer(), nullable=True, default=0),
        sa.Column('citation_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['paper_id'], ['research_papers.paper_id'], ),
        sa.PrimaryKeyConstraint('metric_id'),
        sa.UniqueConstraint('paper_id')
    )

    op.create_table('system_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('log_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('log_id')
    )

    op.create_table('forum_topics',
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, default=False),
        sa.Column('creator_registered_user_id', sa.Integer(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['creator_registered_user_id'], ['registered_users.registered_user_id'], ),
        sa.PrimaryKeyConstraint('topic_id')
    )

    op.create_table('forum_posts',
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('update_date', sa.DateTime(), nullable=True),
        sa.Column('is_solution', sa.Boolean(), nullable=False, default=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('author_registered_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['author_registered_user_id'], ['registered_users.registered_user_id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['forum_topics.topic_id'], ),
        sa.PrimaryKeyConstraint('post_id')
    )

    op.create_table('notifications',
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True, default=False),
        sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('recipient_registered_user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=True),
        sa.Column('object_type', sa.String(length=50), nullable=True),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['recipient_registered_user_id'], ['registered_users.registered_user_id'], ),
        sa.PrimaryKeyConstraint('notification_id')
    )

    # --- Service and Feature Related Entities ---
    op.create_table('journal_finder_service_configs',
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=True),
        sa.Column('last_sync_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('service_id')
    )

    op.create_table('collaboration_workspaces',
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('creation_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('last_modified', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['registered_users.registered_user_id'], ),
        sa.PrimaryKeyConstraint('workspace_id')
    )

    op.create_table('workspace_members',
        sa.Column('membership_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['registered_users.registered_user_id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['collaboration_workspaces.workspace_id'], ),
        sa.PrimaryKeyConstraint('membership_id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user_membership')
    )

    op.create_table('workspace_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('document_type', sa.String(length=50), nullable=False, default='markdown'),
        sa.ForeignKeyConstraint(['creator_id'], ['registered_users.registered_user_id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['collaboration_workspaces.workspace_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('workspace_files',
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('s3_path', sa.String(length=255), nullable=False),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['workspace_documents.id'], ),
        sa.ForeignKeyConstraint(['uploader_id'], ['registered_users.registered_user_id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['collaboration_workspaces.workspace_id'], ),
        sa.PrimaryKeyConstraint('file_id'),
        sa.Index('idx_workspace_files_document_id', 'document_id')
    )

    op.create_table('citations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('paper_id', sa.Integer(), nullable=False),
        sa.Column('style', sa.Enum('APA', 'MLA', 'IEEE', name='citationstyle'), nullable=False),
        sa.Column('bibtex_string', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('download_count', sa.Integer(), nullable=True, default=0),
        sa.Column('copy_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['paper_id'], ['research_papers.paper_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('paper_id', 'style', name='uix_citation_paper_style')
    )

    op.create_table('ai_datasets',
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('dataset_name', sa.String(length=150), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('dataset_id'),
        sa.UniqueConstraint('dataset_name')
    )

    op.create_table('recommendation_engine_configs',
        sa.Column('engine_id', sa.Integer(), nullable=False),
        sa.Column('algorithm_name', sa.String(length=100), nullable=False),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.Column('index_size', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('engine_id')
    )

    # --- FTS5 Support for ResearchPaper ---
    op.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS research_papers_fts USING fts5(
            paper_id UNINDEXED,
            title,
            abstract,
            tokenize = 'porter unicode61'
        );
    ''')

    # Database trigger: After a new ResearchPaper is inserted, add its data to the FTS table
    op.execute('''
        CREATE TRIGGER IF NOT EXISTS research_papers_ai AFTER INSERT ON research_papers BEGIN
            INSERT INTO research_papers_fts (paper_id, title, abstract)
            VALUES (new.paper_id, new.title, new.abstract);
        END;
    ''')

    # Database trigger: After a ResearchPaper is deleted, remove its entry from the FTS table
    op.execute('''
        CREATE TRIGGER IF NOT EXISTS research_papers_ad AFTER DELETE ON research_papers BEGIN
            DELETE FROM research_papers_fts WHERE paper_id = old.paper_id;
        END;
    ''')

    # Database trigger: After a ResearchPaper is updated, update its entry in the FTS table
    op.execute('''
        CREATE TRIGGER IF NOT EXISTS research_papers_au AFTER UPDATE OF title, abstract ON research_papers BEGIN
            UPDATE research_papers_fts SET 
                title = new.title, 
                abstract = new.abstract
            WHERE paper_id = old.paper_id; 
        END;
    ''')


def downgrade():
    op.execute('DROP TRIGGER IF EXISTS research_papers_au;')
    op.execute('DROP TRIGGER IF EXISTS research_papers_ad;')
    op.execute('DROP TRIGGER IF EXISTS research_papers_ai;')
    op.execute('DROP TABLE IF EXISTS research_papers_fts;')
    
    op.drop_table('recommendation_engine_configs')
    op.drop_table('ai_datasets')
    op.drop_table('citations')
    op.drop_table('workspace_files')
    op.drop_table('workspace_documents')
    op.drop_table('workspace_members')
    op.drop_table('collaboration_workspaces')
    op.drop_table('journal_finder_service_configs')
    op.drop_table('notifications')
    op.drop_table('forum_posts')
    op.drop_table('forum_topics')
    op.drop_table('system_logs')
    op.drop_table('paper_metrics')
    op.drop_table('research_papers')
    op.drop_table('premium_users')
    op.drop_table('registered_users')
    op.drop_table('admins')
    op.drop_table('users')
