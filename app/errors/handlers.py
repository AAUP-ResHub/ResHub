from flask import render_template
from app.errors import errors_bp

@errors_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/error.html', 
                          code=404, 
                          message="Page Not Found", 
                          description="The page you are looking for does not exist."), 404

@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/error.html', 
                          code=403, 
                          message="Forbidden", 
                          description="You don't have permission to access this resource."), 403

@errors_bp.app_errorhandler(500)
def internal_error(error):
    return render_template('errors/error.html', 
                          code=500, 
                          message="Internal Server Error", 
                          description="Something went wrong on our end. Please try again later."), 500

@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    return render_template('errors/error.html', 
                          code=400, 
                          message="Bad Request", 
                          description="Your browser sent a request that we could not understand."), 400
