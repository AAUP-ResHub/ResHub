# Flask configuration
SECRET_KEY = 'development-key-replace-with-secure-value-in-production'
DEBUG = True

# Flask-Login configuration
SESSION_PROTECTION = 'strong'
REMEMBER_COOKIE_DURATION = 2592000  # 30 days in seconds
REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS
REMEMBER_COOKIE_HTTPONLY = True

# SQLAlchemy configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Application configuration
APPLICATION_NAME = 'ResHub'
