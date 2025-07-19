from app import create_app
from app.models import User
from app.extensions import db
import getpass

app = create_app()

def create_admin_user():
    with app.app_context():
        print("Create a new admin user")
        username = input("Username: ")
        
        # Check if username already exists
        if User.get_by_username(username):
            print(f"User '{username}' already exists.")
            response = input("Do you want to update this user to be an admin? (y/n): ")
            if response.lower() != 'y':
                return
                
            # Update existing user to admin
            user = User.get_by_username(username)
            user.user_type = 'admin'
            db.session.commit()
            print(f"User '{username}' has been updated to admin type.")
            return
            
        email = input("Email: ")
        
        # Check if email already exists
        if User.get_by_email(email):
            print(f"Email '{email}' is already registered.")
            return
            
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")
        
        if password != password_confirm:
            print("Passwords do not match!")
            return
            
        # Create new user (User.create_user method always creates as 'registered')
        user = User.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Update user type to admin
        user.user_type = 'admin'
        db.session.commit()
        
        print(f"Admin user '{username}' created successfully!")
        
if __name__ == "__main__":
    create_admin_user()
