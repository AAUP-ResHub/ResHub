import os

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'development-key-replace-with-secure-value-in-production')
DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'

# Flask-Login configuration
SESSION_PROTECTION = 'strong'
REMEMBER_COOKIE_DURATION = 2592000  # 30 days in seconds
REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS
REMEMBER_COOKIE_HTTPONLY = True

# SQLAlchemy configuration
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Application configuration
APPLICATION_NAME = 'ResHub'
