from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Import db from extensions to avoid circular imports
from app.extensions import db

# --- User Hierarchy ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Store hashes, not plain text
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # e.g., 'admin', 'registered'
    
    def get_id(self):
        # Flask-Login requires this method
        return str(self.user_id)
    
    @staticmethod
    def get_by_id(user_id):
        # Required by Person 1's auth implementation
        return User.query.filter_by(user_id=int(user_id)).first()
    
    @staticmethod
    def get_by_username(username):
        # Required by Person 1's auth implementation
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_by_email(email):
        # Required by Person 1's auth implementation
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def create_user(username, email, password):
        # Required by Person 1's auth implementation
        user = User(username=username, 
                  email=email, 
                  password_hash=generate_password_hash(password),
                  user_type='registered')
        db.session.add(user)
        db.session.commit()
        return user
    
    def check_password(self, password):
        # Used by Person 1's auth implementation
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Admin(db.Model):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True)
    # Foreign Key to link to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    
    # Relationship to User (one-to-one)
    user = db.relationship('User', backref=db.backref('admin_profile', uselist=False))

    def __repr__(self):
        return f'<Admin ID: {self.admin_id}, User ID: {self.user_id}>'

class RegisteredUser(db.Model):
    __tablename__ = 'registered_users'
    registered_user_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    profile_data = db.Column(db.Text)  # Semantic graph or personal info
    research_stats = db.Column(db.Text)  # Additional user analytics

    # Relationship to User (one-to-one)
    user = db.relationship('User', backref=db.backref('registered_profile', uselist=False))

    # Relationships to other entities
    forum_posts_authored = db.relationship('ForumPost', backref='author', lazy='dynamic', foreign_keys='ForumPost.author_registered_user_id')
    research_papers_owned = db.relationship('ResearchPaper', backref='owner', lazy='dynamic', foreign_keys='ResearchPaper.owner_registered_user_id')
    notifications_received = db.relationship('Notification', backref='recipient', lazy='dynamic', foreign_keys='Notification.recipient_registered_user_id')
    
    # For CollaborationWorkspace
    owned_workspaces = db.relationship('CollaborationWorkspace', backref='owner_user', lazy='dynamic', foreign_keys='CollaborationWorkspace.owner_id')
    workspace_memberships = db.relationship('WorkspaceMember', backref='member_user', lazy='dynamic', foreign_keys='WorkspaceMember.user_id')
    uploaded_files = db.relationship('WorkspaceFile', backref='uploader_user', lazy='dynamic', foreign_keys='WorkspaceFile.uploader_id')

    def __repr__(self):
        return f'<RegisteredUser ID: {self.registered_user_id}, User: {self.user.username if self.user else "N/A"}>'

class PremiumUser(db.Model):
    __tablename__ = 'premium_users'
    premium_user_id = db.Column(db.Integer, primary_key=True)
    registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False, unique=True)
    premium_since = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    additional_quota = db.Column(db.Integer)

    # Relationship to RegisteredUser (one-to-one)
    registered_user = db.relationship('RegisteredUser', backref=db.backref('premium_profile', uselist=False))

    def __repr__(self):
        return f'<PremiumUser ID: {self.premium_user_id}, RegisteredUser ID: {self.registered_user_id}>'

# --- Content and Interaction Entities ---
class ResearchPaper(db.Model):
    __tablename__ = 'research_papers'
    paper_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    abstract = db.Column(db.Text)
    content = db.Column(db.Text)  # Full content or link to it
    publish_date = db.Column(db.Date) 
    
    owner_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)
    
    # One-to-one relationship with PaperMetrics
    metrics = db.relationship('PaperMetrics', backref='paper', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ResearchPaper {self.paper_id}: {self.title[:50]}>'

class PaperMetrics(db.Model):
    __tablename__ = 'paper_metrics'
    metric_id = db.Column(db.Integer, primary_key=True)
    # Foreign Key to link to the ResearchPaper table, ensuring one-to-one
    paper_id = db.Column(db.Integer, db.ForeignKey('research_papers.paper_id'), nullable=False, unique=True) 
    read_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    citation_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<PaperMetrics for PaperID {self.paper_id}>'

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    log_id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.Text, nullable=False)
    log_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Optional: If logs are tied to a specific user (e.g., admin performing action)
    # performing_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))

    def __repr__(self):
        return f'<SystemLog {self.log_id}: {self.action[:50]}>'

class ForumPost(db.Model):
    __tablename__ = 'forum_posts'
    post_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    is_offensive = db.Column(db.Boolean, default=False)
    
    author_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)

    def __repr__(self):
        return f'<ForumPost {self.post_id} by UserID {self.author_registered_user_id}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    recipient_registered_user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)

    def __repr__(self):
        return f'<Notification {self.notification_id} to UserID {self.recipient_registered_user_id}>'

# --- Service and Feature Related Entities ---
class JournalFinderServiceConfig(db.Model):
    __tablename__ = 'journal_finder_service_configs'
    service_id = db.Column(db.Integer, primary_key=True)
    dataset_version = db.Column(db.String(50))
    last_sync_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<JournalFinderServiceConfig {self.service_id}>'

class CollaborationWorkspace(db.Model):
    __tablename__ = 'collaboration_workspaces'
    workspace_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)
    
    # Relationships
    members_in_workspace = db.relationship('WorkspaceMember', backref='workspace', lazy='dynamic', cascade="all, delete-orphan", foreign_keys='WorkspaceMember.workspace_id')
    files_in_workspace = db.relationship('WorkspaceFile', backref='workspace', lazy='dynamic', cascade="all, delete-orphan", foreign_keys='WorkspaceFile.workspace_id')

    def __repr__(self):
        return f'<CollaborationWorkspace {self.workspace_id}: {self.title}>'

class WorkspaceMember(db.Model):
    __tablename__ = 'workspace_members'
    membership_id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('collaboration_workspaces.workspace_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)
    role = db.Column(db.String(50), nullable=False) # e.g., 'viewer', 'editor', 'admin'

    __table_args__ = (db.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user_membership'),)

    def __repr__(self):
        return f'<WorkspaceMember UserID {self.user_id} in WorkspaceID {self.workspace_id} as {self.role}>'

class WorkspaceFile(db.Model):
    __tablename__ = 'workspace_files'
    file_id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    uploader_id = db.Column(db.Integer, db.ForeignKey('registered_users.registered_user_id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('collaboration_workspaces.workspace_id'), nullable=False)

    def __repr__(self):
        return f'<WorkspaceFile {self.file_id}: {self.filename}>'

class AIDataset(db.Model):
    __tablename__ = 'ai_datasets'
    dataset_id = db.Column(db.Integer, primary_key=True)
    dataset_name = db.Column(db.String(150), nullable=False, unique=True)
    type = db.Column(db.String(100)) # e.g., 'summarization', 'critique'
    source = db.Column(db.String(200)) # e.g., 'PubMed', 'Semantic Scholar'
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AIDataset {self.dataset_id}: {self.dataset_name}>'

class RecommendationEngineConfig(db.Model):
    __tablename__ = 'recommendation_engine_configs'
    engine_id = db.Column(db.Integer, primary_key=True)
    algorithm_name = db.Column(db.String(100), nullable=False)
    last_run = db.Column(db.DateTime)
    index_size = db.Column(db.Integer) # Or other relevant config parameters

    def __repr__(self):
        return f'<RecommendationEngineConfig {self.engine_id}: {self.algorithm_name}>'
