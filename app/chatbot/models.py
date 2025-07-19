from app import db
from datetime import datetime
import json
import uuid

class ChatSession(db.Model):
    """Model to store chat sessions to maintain context across interactions."""
    session_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = db.Column(db.String(255), default="New Research Session")
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    chat_logs = db.relationship('ChatLog', backref='session', lazy=True)
    
    def __repr__(self):
        return f"<ChatSession {self.session_id}: {self.title}>"

class ChatLog(db.Model):
    """Model to store chat logs for the research assistant."""
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    session_id = db.Column(db.String(36), db.ForeignKey('chat_session.session_id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_prompt = db.Column(db.Text)
    ai_response = db.Column(db.Text)  # Store the complete AI response
    retrieved_ids = db.Column(db.Text)  # JSON string of retrieved document IDs
    token_in = db.Column(db.Integer)
    token_out = db.Column(db.Integer)
    latency_ms = db.Column(db.Integer)
    hit_rate = db.Column(db.Float)
    thumbs_up_down = db.Column(db.Integer, nullable=True)  # 1 for up, -1 for down, null for no feedback
    
    # Relationships
    feedback = db.relationship('FeedbackDetail', backref='chat_log', lazy=True)
    
    def get_retrieved_ids(self):
        """Convert stored JSON string to Python list."""
        if self.retrieved_ids:
            return json.loads(self.retrieved_ids)
        return []
    
    def set_retrieved_ids(self, ids_list):
        """Convert Python list to JSON string for storage."""
        self.retrieved_ids = json.dumps(ids_list)
    
    def __repr__(self):
        return f"<ChatLog {self.log_id}: {self.user_prompt[:30]}...>"

class FeedbackDetail(db.Model):
    """Model to store detailed feedback on chat responses."""
    feedback_id = db.Column(db.Integer, primary_key=True)
    chat_log_id = db.Column(db.Integer, db.ForeignKey('chat_log.log_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Feedback metrics
    relevance_rating = db.Column(db.Integer)  # 1-5 scale
    accuracy_rating = db.Column(db.Integer)   # 1-5 scale
    completeness_rating = db.Column(db.Integer)  # 1-5 scale
    overall_rating = db.Column(db.Integer)  # 1-5 scale
    feedback_text = db.Column(db.Text)  # Optional text feedback
    
    def __repr__(self):
        return f"<FeedbackDetail {self.feedback_id} for ChatLog {self.chat_log_id}>"
    
class IndexedDocument(db.Model):
    """Model to store metadata for indexed documents."""
    document_id = db.Column(db.String(64), primary_key=True)  # SHA-256 hash
    title = db.Column(db.String(255))
    authors = db.Column(db.Text)  # JSON string of author names
    year = db.Column(db.Integer)
    source = db.Column(db.String(50))  # "arxiv", "semantic_scholar", "core"
    source_id = db.Column(db.String(100))  # Original ID in the source
    file_path = db.Column(db.String(255))
    indexed_at = db.Column(db.DateTime, default=datetime.utcnow)
    chunk_count = db.Column(db.Integer)
    is_ocr_needed = db.Column(db.Boolean, default=False)
    abstract = db.Column(db.Text)  # Paper abstract
    
    def get_authors(self):
        """Convert stored JSON string to Python list."""
        if self.authors:
            return json.loads(self.authors)
        return []
    
    def set_authors(self, authors_list):
        """Convert Python list to JSON string for storage."""
        self.authors = json.dumps(authors_list)
        
    def __repr__(self):
        return f"<IndexedDocument {self.title[:30]}...>"
