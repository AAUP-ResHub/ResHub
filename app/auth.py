from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        if User.get_by_username(username):
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        
        if User.get_by_email(email):
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User.create_user(username, email, password)
        
        if user:
            # Log in the user after registration
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Failed to create user', 'error')
    
    # GET request: render registration form
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return redirect(url_for('auth.login'))
        
        # Get user by email
        user = User.get_by_email(email)
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=remember)
            
            # If there's a next parameter in the URL (for @login_required)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
    
    # GET request: render login form
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))
