from flask import Blueprint, render_template, jsonify, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import RegisteredUser, PremiumUser, db

# Rename blueprint to match what auth.py expects
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Redirect logged-in users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view for logged-in users"""
    return render_template('dashboard.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/api')
def api_index():
    return jsonify({'message': 'Welcome to ResHub API!', 'status': 'running'})


@main_bp.route('/profile')
@login_required
def profile():
    """Semantic graph visualization for premium users"""
    # Get the current user's registered profile
    user = current_user
    registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
    
    if not registered_user:
        flash('User profile not found. Please contact support.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if the user is a premium user
    premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
    
    # Parse research interests if they exist
    research_interests = []
    if registered_user.research_interests:
        research_interests = registered_user.research_interests.lower().split(',')
        research_interests = [interest.strip() for interest in research_interests]
    
    # If premium user, get semantic graph data
    graph_data = None
    similar_researchers = []
    
    if premium_user:
        # Get similar researchers based on research interests
        if research_interests:
            similar_researchers = get_similar_researchers(registered_user.registered_user_id, research_interests)
            
            # Format the data for D3.js visualization
            graph_data = format_graph_data(registered_user, similar_researchers)
    
    return render_template(
        'profile.html',
        user=user,
        registered_user=registered_user,
        is_premium=premium_user is not None,
        research_interests=research_interests,
        graph_data=graph_data if graph_data else None,
        similar_researchers=similar_researchers
    )


@main_bp.route('/semantic-graph/edit_topics', methods=['POST'])
@login_required
def edit_topics():
    """Edit research topics for premium users"""
    # Get the current user's registered profile
    user = current_user
    registered_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
    
    if not registered_user:
        return jsonify({'success': False, 'message': 'User profile not found'}), 404
    
    # Check if the user is a premium user
    premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
    
    if not premium_user:
        return jsonify({'success': False, 'message': 'This feature is only available for premium users'}), 403
    
    # Get the new topics from the form
    topics = request.form.get('topics', '')
    
    # Normalize topics (lowercase, strip whitespace)
    normalized_topics = normalize_topics(topics)
    
    # Update the user's research interests
    registered_user.research_interests = normalized_topics
    
    # Update the semantic graph data for premium user
    topic_vector = create_topic_vector(normalized_topics)
    premium_user.semantic_graph = topic_vector
    
    # Save changes to database
    db.session.commit()
    
    flash('Research interests updated successfully', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/api/topic_aliases')
@login_required
def get_topic_aliases_api():
    """Return the topic aliases dictionary"""
    # Check if user is premium
    registered_user = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    if not registered_user:
        return jsonify({'error': 'User not found'}), 404
        
    premium_user = PremiumUser.query.filter_by(registered_user_id=registered_user.registered_user_id).first()
    if not premium_user:
        return jsonify({'error': 'Premium access required'}), 403
    
    aliases = get_topic_aliases()
    return jsonify(aliases)


# Helper functions
def get_topic_aliases():
    """Get the mapping of topic aliases"""
    # This could be stored in a database table in the future
    return {
        "ml": "machine learning",
        "ai": "artificial intelligence",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "ir": "information retrieval",
        "rl": "reinforcement learning",
        "nn": "neural networks",
        "dl": "deep learning",
        "nlg": "natural language generation",
        "nlu": "natural language understanding"
    }


def normalize_topics(topics_string):
    """Normalize topics by converting to lowercase, removing extra whitespace, and handling aliases"""
    if not topics_string:
        return ''
    
    # Split by comma, strip whitespace, and convert to lowercase
    topics = [t.strip().lower() for t in topics_string.split(',') if t.strip()]
    
    # Replace aliases with their canonical forms
    aliases = get_topic_aliases()
    normalized = [aliases.get(t, t) for t in topics]
    
    # Remove duplicates while maintaining order
    unique_topics = []
    for topic in normalized:
        if topic not in unique_topics:
            unique_topics.append(topic)
    
    return ', '.join(unique_topics)


def create_topic_vector(topics_string):
    """Convert topics string to a vector representation"""
    if not topics_string:
        return {}
    
    topics = [t.strip().lower() for t in topics_string.split(',') if t.strip()]
    return {topic: 1 for topic in topics}


def get_similar_researchers(current_user_id, current_user_interests):
    """Find researchers with similar interests"""
    # Find all users who have research interests
    users_with_interests = RegisteredUser.query.filter(
        RegisteredUser.research_interests.isnot(None),
        RegisteredUser.research_interests != '',
        RegisteredUser.registered_user_id != current_user_id
    ).all()
    
    similar_users = []
    for user in users_with_interests:
        if not user.research_interests:
            continue
            
        # Get user's interests
        user_interests = [t.strip().lower() for t in user.research_interests.split(',')]
        
        # Find shared interests
        shared_interests = list(set(current_user_interests) & set(user_interests))
        
        if shared_interests:  # Only include users with at least one shared interest
            # Calculate similarity score (simple version - percentage of overlap)
            # For a more advanced version, we could use cosine similarity with TF-IDF vectors
            similarity = len(shared_interests) / max(len(current_user_interests), len(user_interests))
            similarity_percent = int(similarity * 100)
            
            user_data = {
                'id': user.registered_user_id,
                'name': f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.user.username,
                'interests': user_interests,
                'shared_interests': shared_interests,
                'similarity': similarity_percent
            }
            similar_users.append(user_data)
    
    # Sort by similarity score (descending)
    return sorted(similar_users, key=lambda x: x['similarity'], reverse=True)


def format_graph_data(current_user, similar_researchers):
    """Format the data for D3.js visualization"""
    # Create nodes and links for the graph
    nodes = [{
        'id': current_user.registered_user_id,
        'name': f"{current_user.first_name} {current_user.last_name}" if current_user.first_name and current_user.last_name else current_user.user.username,
        'group': 1,  # Current user is in group 1
        'user_id': current_user.user_id,  # Add user_id for messaging functionality
    }]
    
    links = []
    
    # Add similar researchers as nodes
    for i, researcher in enumerate(similar_researchers):
        # Get the user_id for this researcher to enable messaging
        researcher_record = RegisteredUser.query.get(researcher['id'])
        user_id = researcher_record.user_id if researcher_record else None
        
        nodes.append({
            'id': researcher['id'],
            'name': researcher['name'],
            'group': 2,  # Similar researchers are in group 2
            'similarity': researcher['similarity'],
            'shared_interests': researcher['shared_interests'],
            'user_id': user_id  # Add user_id for messaging functionality
        })
        
        # Create a link between the current user and this researcher
        links.append({
            'source': current_user.registered_user_id,
            'target': researcher['id'],
            'value': researcher['similarity']  # Link strength based on similarity
        })
    
    return {'nodes': nodes, 'links': links}
