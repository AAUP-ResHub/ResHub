from app import create_app, db
from flask_migrate import upgrade

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Apply all pending migrations
        upgrade()
        print("Migrations applied successfully!")
