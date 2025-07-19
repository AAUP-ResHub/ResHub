"""
Integration test route for verifying feature integration between teammates
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import current_user, login_required
import datetime

from app.extensions import db
from app.models import Notification

# Create blueprint for integration testing
integration_test_bp = Blueprint('integration_test', __name__, url_prefix='/integration')

@integration_test_bp.route('/dashboard', methods=['GET'])
@login_required
def integration_dashboard():
    """
    Render the integration test dashboard showing all integrated features
    """
    return render_template('integration_dashboard.html')

@integration_test_bp.route('/trigger-notification', methods=['POST'])
@login_required
def trigger_notification():
    """
    Create a test notification for the current user
    """
    try:
        # Get notification type
        data = request.get_json()
        notification_type = data.get('type', 'message')
        
        # Create notification based on type
        notification = Notification(
            recipient_registered_user_id=current_user.registered_user_id,
            sent_date=datetime.datetime.utcnow(),
            is_read=False
        )
        
        if notification_type == 'message':
            notification.message = 'You have a new test message from the integration system.'
            notification.action = 'new_message'
            notification.object_type = 'message'
            notification.object_id = 12345
        elif notification_type == 'workspace':
            notification.message = 'You have been invited to the workspace "Integration Test".'
            notification.action = 'workspace_invite'
            notification.object_type = 'workspace'
            notification.object_id = 67890
        elif notification_type == 'citation':
            notification.message = 'Your paper "Integration Testing" has received a new citation.'
            notification.action = 'citation_alert'
            notification.object_type = 'paper'
            notification.object_id = 54321
        else:
            notification.message = f'Test notification ({notification_type})'
            notification.action = 'test'
            
        # Save notification
        db.session.add(notification)
        db.session.commit()
        
        # Get unread count
        unread_count = Notification.query.filter_by(
            recipient_registered_user_id=current_user.registered_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'notification_id': notification.notification_id,
            'message': notification.message,
            'unread_count': unread_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating test notification: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
