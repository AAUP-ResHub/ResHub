#for testing the relations between ResearchPaper and PaperMetrics and show how the data will be 

from app import create_app, db
from app.models import ResearchPaper, PaperMetrics, User, RegisteredUser
from datetime import date, datetime
import random

def seed_papers():
    """
    Seed the database with three example papers and their metrics
    to test the relationship between ResearchPaper and PaperMetrics.
    """
    app = create_app()
    
    with app.app_context():
        # First check if we already have a user to associate with the papers
        user = User.query.first()
        reg_user = None
        
        if not user:
            # Create a test user if none exists
            print("Creating test user...")
            user = User(
                username="testuser",
                email="test@example.com",
                user_type="registered"
            )
            # Set password (using the UserMixin methods if available)
            if hasattr(user, 'set_password'):
                user.set_password("password123")
            else:
                # Fallback if there's no set_password method
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash("password123")
            
            db.session.add(user)
            db.session.flush()  # To get the user ID without committing
            
            # Create a registered user profile
            reg_user = RegisteredUser(
                user_id=user.user_id,
                first_name="Test",
                last_name="User"
            )
            db.session.add(reg_user)
            db.session.commit()
        else:
            # Get the registered user profile for the existing user
            reg_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
            if not reg_user:
                print("Error: Found user but no registered user profile")
                return
        
        # Create three example papers
        papers = [
            ResearchPaper(
                title="Advancements in Machine Learning for Natural Language Processing",
                abstract="This paper explores recent advancements in machine learning techniques applied to natural language processing tasks, with a focus on transformer models.",
                content="[Full content of the paper would be here...]",
                publish_date=date(2023, 8, 15),
                owner_registered_user_id=reg_user.registered_user_id
            ),
            ResearchPaper(
                title="Climate Change Impact on Agricultural Productivity",
                abstract="A comprehensive analysis of how climate change affects agricultural productivity across different regions and crop types.",
                content="[Detailed analysis and research findings...]",
                publish_date=date(2024, 2, 10),
                owner_registered_user_id=reg_user.registered_user_id
            ),
            ResearchPaper(
                title="Novel Approaches to Renewable Energy Storage",
                abstract="This research investigates innovative methods for storing renewable energy to address intermittency issues in solar and wind power generation.",
                content="[Research methodology and results...]",
                publish_date=date(2024, 4, 22),
                owner_registered_user_id=reg_user.registered_user_id
            )
        ]
        
        # Add papers to the database
        for paper in papers:
            db.session.add(paper)
        
        # Commit to get paper IDs
        db.session.commit()
        
        # Create metrics for each paper
        for paper in papers:
            # Generate some random metrics for testing
            metrics = PaperMetrics(
                paper_id=paper.paper_id,
                read_count=random.randint(50, 500),
                download_count=random.randint(10, 100),
                citation_count=random.randint(0, 50)
            )
            db.session.add(metrics)
        
        # Commit the metrics
        db.session.commit()
        
        print(f"Successfully created {len(papers)} papers with their associated metrics")
        
        # Print out the papers and their metrics for verification
        for paper in papers:
            print(f"\nPaper: {paper.title}")
            print(f"Paper ID: {paper.paper_id}")
            print(f"Metrics: read_count={paper.metrics.read_count}, "
                  f"download_count={paper.metrics.download_count}, "
                  f"citation_count={paper.metrics.citation_count}")

if __name__ == "__main__":
    seed_papers()
