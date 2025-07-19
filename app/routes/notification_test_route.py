"""
Test route for the notification system integration
"""
from flask import Blueprint, render_template
from flask_login import login_required

# Create a blueprint for the notification test page
notification_test_bp = Blueprint('notification_test', __name__)

@notification_test_bp.route('/notification-test', methods=['GET'])
@login_required
def notification_test():
    """
    Render the notification system test page
    """
    return render_template('notification_test.html')
