"""
This is a modified version of the models.py file with the extend_existing option added
to the Notification model to prevent the SQLAlchemy table conflict.
"""

# Use this file as a patch to fix the duplicate table definition
__table_args__ = {'extend_existing': True}

# Add this line to the Notification class in models.py:
# __table_args__ = {'extend_existing': True}
