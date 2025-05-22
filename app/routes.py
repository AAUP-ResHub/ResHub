from flask import Blueprint, render_template, jsonify

# Rename blueprint to match what auth.py expects
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/api')
def api_index():
    return jsonify({'message': 'Welcome to ResHub API!', 'status': 'running'})
