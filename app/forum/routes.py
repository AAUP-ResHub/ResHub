from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from markdown_it import MarkdownIt
import bleach
from sqlalchemy import desc
from datetime import datetime
from flask_wtf import FlaskForm

from app.forum import forum_bp
from app.models import ForumTopic, ForumPost, RegisteredUser
from app.extensions import db

# Configure Markdown renderer with safe defaults
md = MarkdownIt('commonmark', {'html': False, 'linkify': True})

# Configure bleach for sanitizing HTML
ALLOWED_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'abbr', 'acronym', 'b', 'blockquote', 
                'code', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 'span', 'div', 'img', 'br']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
}

def is_admin():
    """Check if current user is an admin"""
    if not current_user.is_authenticated:
        return False
    
    # Check if user has admin profile
    return hasattr(current_user, 'admin_profile') and current_user.admin_profile is not None

def render_markdown(text):
    """Render markdown text to safe HTML"""
    # First render markdown to HTML
    html = md.render(text)
    
    # Then sanitize the HTML
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    return clean_html

@forum_bp.route('/')
def index():
    """Display list of all forum topics"""
    page = request.args.get('page', 1, type=int)
    topics = ForumTopic.query.order_by(desc(ForumTopic.timestamp)).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('forum/index.html', topics=topics)

@forum_bp.route('/<int:topic_id>')
def topic_detail(topic_id):
    """Display a specific topic and its posts"""
    topic = ForumTopic.query.get_or_404(topic_id)
    page = request.args.get('page', 1, type=int)
    
    # Get posts with pagination
    posts = ForumPost.query.filter_by(topic_id=topic_id).order_by(ForumPost.timestamp).paginate(
        page=page, per_page=20, error_out=False)
    
    # Get pinned posts (always shown at the top)
    pinned_posts = ForumPost.query.filter_by(topic_id=topic_id, is_pinned=True).order_by(ForumPost.timestamp).all()
    
    # Process markdown for display
    for post in posts.items:
        post.rendered_content = render_markdown(post.content)
    
    for post in pinned_posts:
        post.rendered_content = render_markdown(post.content)
    
    # Create a form for CSRF protection
    form = FlaskForm()
    
    return render_template('forum/topic.html', topic=topic, posts=posts, pinned_posts=pinned_posts, form=form)

@forum_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_topic():
    """Create a new forum topic"""
    form = FlaskForm()
    if form.validate_on_submit():
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required', 'danger')
            return redirect(url_for('forum.new_topic'))
        
        # Check if user has a registered profile
        if not hasattr(current_user, 'registered_profile') or current_user.registered_profile is None:
            # Create a registered profile for the user if not exists
            registered_user = RegisteredUser(user_id=current_user.user_id)
            db.session.add(registered_user)
            db.session.commit()
            # Refresh the user object to get the new registered_profile
            db.session.refresh(current_user)
        
        # Create new topic
        topic = ForumTopic(
            title=title,
            created_by=current_user.registered_profile.registered_user_id
        )
        
        db.session.add(topic)
        db.session.commit()
        
        # Create initial post
        post = ForumPost(
            content=content,
            topic_id=topic.topic_id,
            author_registered_user_id=current_user.registered_profile.registered_user_id
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('Topic created successfully!', 'success')
        return redirect(url_for('forum.topic_detail', topic_id=topic.topic_id))
    
    return render_template('forum/new_topic.html', form=form)

@forum_bp.route('/<int:topic_id>/reply', methods=['POST'])
@login_required
def reply(topic_id):
    """Add a reply to a topic"""
    form = FlaskForm()
    if not form.validate_on_submit():
        return abort(400)  # Bad request if CSRF validation fails
        
    topic = ForumTopic.query.get_or_404(topic_id)
    content = request.form.get('content')
    
    # Check if user has a registered profile
    if not hasattr(current_user, 'registered_profile') or current_user.registered_profile is None:
        # Create a registered profile for the user if not exists
        registered_user = RegisteredUser(user_id=current_user.user_id)
        db.session.add(registered_user)
        db.session.commit()
        # Refresh the user object to get the new registered_profile
        db.session.refresh(current_user)
    
    if not content:
        flash('Reply content cannot be empty', 'danger')
        return redirect(url_for('forum.topic_detail', topic_id=topic_id))
    
    # Create new post
    post = ForumPost(
        content=content,
        topic_id=topic_id,
        author_registered_user_id=current_user.registered_profile.registered_user_id
    )
    
    db.session.add(post)
    db.session.commit()
    
    flash('Reply added successfully!', 'success')
    return redirect(url_for('forum.topic_detail', topic_id=topic_id))

@forum_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Edit a forum post"""
    post = ForumPost.query.get_or_404(post_id)
    
    # Check if user is the author
    if post.author_registered_user_id != current_user.registered_profile.registered_user_id and not is_admin():
        abort(403)
    
    # Create a form for CSRF protection
    form = FlaskForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        content = request.form.get('content')
        
        if not content:
            flash('Post content cannot be empty', 'danger')
            return redirect(url_for('forum.edit_post', post_id=post_id))
        
        post.content = content
        post.is_edited = True
        db.session.commit()
        
        flash('Post updated successfully!', 'success')
        return redirect(url_for('forum.topic_detail', topic_id=post.topic_id))
    
    return render_template('forum/edit_post.html', post=post, form=form)

@forum_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete a forum post"""
    form = FlaskForm()
    if not form.validate_on_submit():
        return abort(400)  # Bad request if CSRF validation fails
        
    post = ForumPost.query.get_or_404(post_id)
    
    # Check if user is the author or an admin
    if post.author_registered_user_id != current_user.registered_profile.registered_user_id and not is_admin():
        abort(403)
    
    topic_id = post.topic_id
    
    # Check if this is the only post in the topic
    post_count = ForumPost.query.filter_by(topic_id=topic_id).count()
    is_first_post = ForumPost.query.filter_by(topic_id=topic_id).order_by(ForumPost.timestamp).first().post_id == post_id
    
    # If it's the only post or the first post, delete the entire topic
    if post_count == 1 or is_first_post:
        topic = ForumTopic.query.get_or_404(topic_id)
        db.session.delete(topic)  # This will cascade delete all posts
        db.session.commit()
        
        flash('Topic deleted successfully!', 'success')
        return redirect(url_for('forum.index'))
    else:
        # Just delete the post
        db.session.delete(post)
        db.session.commit()
        
        flash('Post deleted successfully!', 'success')
        return redirect(url_for('forum.topic_detail', topic_id=topic_id))

@forum_bp.route('/post/<int:post_id>/pin', methods=['POST'])
@login_required
def toggle_pin(post_id):
    """Pin or unpin a post (admin only)"""
    form = FlaskForm()
    if not form.validate_on_submit():
        return abort(400)  # Bad request if CSRF validation fails
        
    if not is_admin():
        abort(403)
    
    post = ForumPost.query.get_or_404(post_id)
    post.is_pinned = not post.is_pinned
    db.session.commit()
    
    action = "pinned" if post.is_pinned else "unpinned"
    flash(f'Post {action} successfully!', 'success')
    
    return redirect(url_for('forum.topic_detail', topic_id=post.topic_id))

@forum_bp.route('/user/<int:user_id>')
def user_posts(user_id):
    """View all posts by a specific user"""
    user = RegisteredUser.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    
    posts = ForumPost.query.filter_by(author_registered_user_id=user_id).order_by(
        desc(ForumPost.timestamp)).paginate(page=page, per_page=10, error_out=False)
    
    # Process markdown for display
    for post in posts.items:
        post.rendered_content = render_markdown(post.content)
    
    return render_template('forum/user_posts.html', user=user, posts=posts)
