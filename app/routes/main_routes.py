from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from app.models import User, CollaborationWorkspace as Workspace, WorkspaceMember
from app import db

# Create main blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Landing page route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page for authenticated users"""
    # Workspace functionality has been removed
    
    return render_template('dashboard.html', 
                           title='Dashboard')

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html', title='About')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html', title='Contact')
