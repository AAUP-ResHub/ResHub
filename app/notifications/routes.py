from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Notification
from sqlalchemy import desc

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def index():
    """Show all notifications"""
    try:
        # Get all notifications for the current user
        notifications = Notification.query.filter_by(
            user_id=current_user.user_id
        ).order_by(desc(Notification.timestamp)).all()
        
        # Mark all unread notifications as read
        unread_notifications = [n for n in notifications if not n.is_read]
        for notification in unread_notifications:
            notification.is_read = True
        
        db.session.commit()
    except Exception as e:
        print(f"Error accessing notifications: {e}")
        notifications = []
    
    return render_template('notifications/index.html', notifications=notifications)

@notifications_bp.route('/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        
        # Ensure the notification belongs to the current user
        if notification.recipient_registered_user_id != current_user.user_id:
            flash('You do not have permission to modify this notification.', 'danger')
            return redirect(url_for('notifications.index'))
        
        notification.is_read = True
        db.session.commit()
    except Exception as e:
        flash(f'Could not mark notification as read: Database error', 'danger')
    
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/count')
@login_required
def count():
    """Get the number of unread notifications for the current user"""
    try:
        count = Notification.query.filter_by(
            user_id=current_user.user_id,
            is_read=False
        ).count()
    except Exception:
        count = 0
    
    return {'count': count}
