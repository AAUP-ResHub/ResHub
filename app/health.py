"""
Health check routes for application monitoring.

These endpoints provide basic health status information about the application
and its dependencies (database, vector store, etc).
"""
import time
from datetime import datetime

from sqlalchemy import text
from flask import Blueprint, jsonify, current_app

from app.extensions import db

bp = Blueprint('health', __name__, url_prefix='/health')


@bp.route('/')
def health():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'ok',
        'version': current_app.config.get('VERSION', '1.0.0'),
        'timestamp': datetime.now().isoformat()
    })


@bp.route('/complete')
def complete_health():
    """
    Complete health check with all system components.
    
    This checks:
    - Database connection
    - Vector database connection (if configured)
    - Response time
    """
    start_time = time.time()
    health_data = {
        'status': 'ok',
        'version': current_app.config.get('VERSION', '1.0.0'),
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check database
    try:
        db_start = time.time()
        db.session.execute(text('SELECT 1'))
        db_end = time.time()
        health_data['components']['database'] = {
            'status': 'ok',
            'latency_ms': round((db_end - db_start) * 1000, 2)
        }
    except Exception as e:
        health_data['status'] = 'error'
        health_data['components']['database'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Check vector database if configured
    if current_app.config.get('VECTOR_DB_HOST'):
        try:
            vector_start = time.time()
            # Import here to avoid circular import
            from app.chatbot.vector_store import get_vector_client
            vector_client = get_vector_client()
            collections = vector_client.get_collections()
            vector_end = time.time()
            health_data['components']['vector_database'] = {
                'status': 'ok',
                'latency_ms': round((vector_end - vector_start) * 1000, 2),
                'collections_count': len(collections)
            }
        except Exception as e:
            health_data['components']['vector_database'] = {
                'status': 'error',
                'error': str(e)
            }
            # Only mark overall status as error if database is also down
            if health_data['components'].get('database', {}).get('status') == 'error':
                health_data['status'] = 'error'
    
    # Application runtime information
    health_data['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    return jsonify(health_data)


@bp.route('/readiness')
def readiness():
    """
    Readiness probe for Kubernetes or other orchestration platforms.
    
    Returns 200 if the application is ready to accept traffic,
    503 if not.
    """
    try:
        # Check database connectivity
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ready'})
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'reason': str(e)
        }), 503
