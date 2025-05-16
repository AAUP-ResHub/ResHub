from flask import Blueprint, render_template, jsonify

routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/')
def index():
    return jsonify({"message": "Welcome to ResHub API"})

@routes_bp.route('/health')
def health_check():
    return jsonify({"status": "healthy"})
