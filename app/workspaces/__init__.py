from flask import Blueprint

# Define the workspaces blueprint
workspaces_bp = Blueprint('workspaces', __name__, url_prefix='/workspaces', template_folder='templates')

# Import routes to register them with the blueprint
from . import routes
