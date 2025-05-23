from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user

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
