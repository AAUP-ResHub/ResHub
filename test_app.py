"""
Temporary test script to run the ResHub app with messaging functionality
"""
from app import create_app
import sys
import os

# Monkey patch the models module to fix the table conflict
# This is a temporary solution to avoid modifying the actual files
import importlib.util
import types

def run_app():
    try:
        # Create the Flask application
        app = create_app()
        
        # Run the application with debug mode enabled
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_app()
