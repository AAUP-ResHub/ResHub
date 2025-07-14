from flask import jsonify
from flask_login import login_required, current_user
from . import api_bp
from app.models import RegisteredUser  # To fetch user details

@api_bp.route('/recommend')
@login_required
def get_recommendations():
    """Returns a list of recommended researchers for the current user."""
    # Ensure the current user has a registered profile
    if not hasattr(current_user, 'registered_profile') or not current_user.registered_profile:
        return jsonify({'error': 'Current user does not have a registered profile'}), 400
    
    # Access the recommender service from the app context
    from flask import current_app
    recommender_service = current_app.recommender_service
    
    current_reg_user_id = current_user.registered_profile.registered_user_id
    
    recommended_ids = recommender_service.recommend(current_reg_user_id, top_n=5)
    
    # Fetch user details for the recommended IDs to return more useful data
    recommended_users_data = []
    if recommended_ids:
        recommended_reg_users = RegisteredUser.query.filter(RegisteredUser.registered_user_id.in_(recommended_ids)).all()
        for reg_user in recommended_reg_users:
            recommended_users_data.append({
                'registered_user_id': reg_user.registered_user_id,
                'username': reg_user.user.username,
                'full_name': f"{reg_user.first_name or ''} {reg_user.last_name or ''}".strip(),
                # Add other public profile data as needed
            })

    return jsonify(recommended_users_data)
