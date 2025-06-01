from flask import Blueprint

# Define the blueprint
search_bp = Blueprint('search', __name__, template_folder='templates')

from . import routes  # Import routes to register them with the blueprint