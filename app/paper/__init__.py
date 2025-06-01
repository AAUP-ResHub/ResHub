from flask import Blueprint

paper_bp = Blueprint('paper', __name__, url_prefix='/papers')

from app.paper import routes
