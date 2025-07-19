"""
Security configurations for the ResHub application.
"""
from flask import Flask

def configure_csp(app: Flask):
    """
    Configure Content Security Policy headers.
    
    This function adds after_request handlers to the Flask app
    to set appropriate CSP headers that allow Quill.js and other scripts to run.
    """
    @app.after_request
    def add_security_headers(response):
        # Configure CSP to allow Quill.js and other necessary resources
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com https://stackpath.bootstrapcdn.com https://d3js.org",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com https://stackpath.bootstrapcdn.com",
            "img-src 'self' data: blob: https://ui-avatars.com",
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            "connect-src 'self'",
            "frame-src 'self'",
            "object-src 'none'"
        ]
        
        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
        return response

    return app
