from flask import Blueprint, render_template, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return "<h1>Welcome to ResHub!</h1><p>The application is running successfully.</p>"

@main_bp.route('/api')
def api_index():
    return jsonify({'message': 'Welcome to ResHub API!', 'status': 'running'})
