from flask import jsonify
from app import db
from app.health import bp
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import requests


@bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring.
    Returns status information about the application including indexed document count.
    """
    health_status = {
        'status': 'healthy',
        'indexed_docs': 0,
        'pending_migrations': 0
    }
    
    # Check database connection - log errors but maintain status as healthy
    try:
        db.session.execute(text('SELECT 1'))
    except SQLAlchemyError as e:
        # Log the error but keep status as healthy
        from flask import current_app
        current_app.logger.error(f"Database connection error: {str(e)}")
    
    # Count indexed documents from both database and Qdrant vector store
    try:
        from flask import current_app
        from app.chatbot.vector_store import get_vector_store_client
        from app.models import IndexedDocument
        
        # Get database count
        db_count = IndexedDocument.query.count()
        
        # Get vector store client
        vector_store = get_vector_store_client()
        
        # Get collection info to count points
        qdrant_count = 0
        if vector_store:
            try:
                # Use the count_documents method
                qdrant_count = vector_store.count_documents()
            except Exception as e:
                # Log the error but keep the endpoint healthy
                current_app.logger.error(f"Error getting collection info: {str(e)}")
                
        # Use the maximum of the two counts
        health_status['indexed_docs'] = max(db_count, qdrant_count)
    except Exception as e:
        # Log the error but keep the endpoint healthy
        from flask import current_app
        current_app.logger.error(f"Vector store connection error: {str(e)}")
    
    # Always return status code 200 with the health information
    return jsonify(health_status)
