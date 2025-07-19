from app import create_app
from app.models import SiteSetting
from app.extensions import db

# Create an application context
app = create_app()
with app.app_context():
    # Create only the SiteSetting table if it doesn't exist
    SiteSetting.__table__.create(db.engine, checkfirst=True)
    print("SiteSetting table created successfully!")
    
    # Add some initial settings
    if not SiteSetting.query.filter_by(key='footer_text').first():
        footer = SiteSetting(
            key='footer_text', 
            value='© 2025 ResHub - All rights reserved', 
            description='Text displayed in the site footer'
        )
        db.session.add(footer)
    
    if not SiteSetting.query.filter_by(key='primary_color').first():
        color = SiteSetting(
            key='primary_color', 
            value='#4a86e8', 
            description='Primary brand color'
        )
        db.session.add(color)
    
    if not SiteSetting.query.filter_by(key='site_name').first():
        site_name = SiteSetting(
            key='site_name', 
            value='ResHub', 
            description='Name of the site displayed in headers and titles'
        )
        db.session.add(site_name)
    
    db.session.commit()
    print("Initial settings created!")
