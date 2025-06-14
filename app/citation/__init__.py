from flask import Blueprint

citation_bp = Blueprint('citation', __name__, url_prefix='/citation')

from app.citation import routes
