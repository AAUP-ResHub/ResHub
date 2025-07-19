"""
ResHub Notification Routes
Handles API endpoints for notification retrieval and management
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from sqlalchemy import desc
from datetime import datetime, timedelta
import time

from app.extensions import db
from app.models import Notification
from app.services.notification_service import send_notification

# Create blueprint
notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notification_bp.route('', methods=['GET'])
@login_required
def get_notifications():
    """
    Get notifications for the current user
    Optional query param 'since' for timestamp-based filtering (unix timestamp)
    Optional query param 'limit' for pagination (default 20)
    """
    try:
        # Check if user has registered profile
        if not current_user.registered_profile:
            return jsonify({'error': 'User profile not found'}), 404
            
        registered_user_id = current_user.registered_profile.registered_user_id
        
        # Get query parameters
        since = request.args.get('since', type=int)
        limit = min(int(request.args.get('limit', 20)), 50)  # Cap at 50
        filter_type = request.args.get('filter', 'all').lower()  # all, read, unread
        
        # Base query
        query = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id
        ).order_by(desc(Notification.sent_date))
        
        # Add filter for read/unread status
        if filter_type == 'read':
            query = query.filter(Notification.is_read == True)
        elif filter_type == 'unread':
            query = query.filter(Notification.is_read == False)
        # 'all' doesn't add any filter
        
        # Add since filter if provided
        if since:
            since_datetime = datetime.fromtimestamp(since)
            query = query.filter(Notification.sent_date > since_datetime)
        
        # Get notifications and count
        notifications = query.limit(limit).all()
        unread_count = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id,
            is_read=False
        ).count()
        
        # Format notifications
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': notification.notification_id,
                'title': f'{notification.action.title()} Notification' if notification.action else 'Notification',
                'message': notification.message,
                'created_at': notification.sent_date.isoformat(),
                'is_read': notification.is_read,
                'type': notification.action,
                'action': notification.action,
                'object_type': notification.object_type,
                'object_id': notification.object_id,
                'actor': {
                    'id': notification.actor_registered_user_id,
                    # These would be fetched from User/RegisteredUser in a real implementation
                    # But simplified for demonstration
                }
            })
        
        # Return response with current timestamp for client caching
        return jsonify({
            'notifications': notification_data,
            'unread_count': unread_count,
            'timestamp': int(time.time())
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching notifications: {e}")
        return jsonify({'error': 'Failed to fetch notifications'}), 500

@notification_bp.route('/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a single notification as read"""
    try:
        # Check if user has registered profile
        if not current_user.registered_profile:
            return jsonify({'error': 'User profile not found'}), 404
            
        registered_user_id = current_user.registered_profile.registered_user_id
        
        notification = Notification.query.filter_by(
            notification_id=notification_id,
            recipient_registered_user_id=registered_user_id
        ).first_or_404()
        
        notification.is_read = True
        db.session.commit()
        
        # Get updated unread count
        unread_count = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'notification_id': notification_id,
            'unread_count': unread_count
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({'error': 'Failed to update notification'}), 500

@notification_bp.route('/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark multiple notifications as read"""
    try:
        # Check if user has registered profile
        if not current_user.registered_profile:
            return jsonify({'error': 'User profile not found'}), 404
            
        registered_user_id = current_user.registered_profile.registered_user_id
        
        data = request.get_json()
        notification_ids = data.get('notification_ids', [])
        
        if not notification_ids:
            return jsonify({'error': 'No notification IDs provided'}), 400
        
        # Update notifications
        result = Notification.query.filter(
            Notification.notification_id.in_(notification_ids),
            Notification.recipient_registered_user_id == registered_user_id
        ).update({'is_read': True}, synchronize_session=False)
        
        db.session.commit()
        
        # Get updated unread count
        unread_count = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'notifications_updated': result,
            'unread_count': unread_count
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking notifications as read: {e}")
        return jsonify({'error': 'Failed to update notifications'}), 500

@notification_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications for the current user as read"""
    try:
        # Check if user has registered profile
        if not current_user.registered_profile:
            return jsonify({'error': 'User profile not found'}), 404
            
        registered_user_id = current_user.registered_profile.registered_user_id
        
        # Update all unread notifications
        result = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id,
            is_read=False
        ).update({'is_read': True}, synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'notifications_updated': result,
            'unread_count': 0
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'error': 'Failed to update notifications'}), 500

@notification_bp.route('/delete/<notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        # Check if user has registered profile
        if not current_user.registered_profile:
            return jsonify({'error': 'User profile not found'}), 404
            
        registered_user_id = current_user.registered_profile.registered_user_id
        
        notification = Notification.query.filter_by(
            notification_id=notification_id,
            recipient_registered_user_id=registered_user_id
        ).first_or_404()
        
        db.session.delete(notification)
        db.session.commit()
        
        # Get updated unread count
        unread_count = Notification.query.filter_by(
            recipient_registered_user_id=registered_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'notification_id': notification_id,
            'unread_count': unread_count
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting notification: {e}")
        return jsonify({'error': 'Failed to delete notification'}), 500

@notification_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_old_notifications():
    """
    Clean up old read notifications
    This endpoint is primarily for admin users or scheduled tasks
    """
    try:
        # Get retention days from config or use default (30 days)
        retention_days = current_app.config.get('NOTIFICATION_RETENTION_DAYS', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete old read notifications
        result = Notification.query.filter(
            Notification.sent_date < cutoff_date,
            Notification.is_read == True
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'notifications_deleted': result,
            'retention_days': retention_days
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cleaning up notifications: {e}")
        return jsonify({'error': 'Failed to clean up notifications'}), 500

# Test endpoint to create a notification (for development only)
@notification_bp.route('/test/create', methods=['POST'])
@login_required
def create_test_notification():
    """Create a test notification for the current user (development only)"""
    if not current_app.debug:
        return jsonify({'error': 'This endpoint is only available in debug mode'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', 'Test notification')
        action = data.get('action', 'test')
        
        # Create notification directly
        notification = Notification(
            recipient_registered_user_id=current_user.registered_user_id,
            message=message,
            action=action if hasattr(Notification, 'action') else None
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'notification_id': notification.notification_id,
            'message': notification.message
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating test notification: {e}")
        return jsonify({'error': 'Failed to create test notification'}), 500
