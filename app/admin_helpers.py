from flask import url_for
from urllib.parse import urlparse, parse_qsl, urlencode

def register_template_helpers(app):
    """Register custom template helpers for the admin interface"""
    
    @app.template_global()
    def add_url_params(url, **params):
        """Add parameters to the URL's query string."""
        # Parse the URL
        parts = urlparse(url)
        
        # Parse query parameters
        query_params = dict(parse_qsl(parts.query))
        
        # Update with new parameters
        query_params.update(params)
        
        # Return URL with updated query string
        from urllib.parse import urlunparse
        parts_list = list(parts)
        parts_list[4] = urlencode(query_params)
        return urlunparse(parts_list)

    @app.template_global()
    def remove_url_params(url, **params):
        """Remove parameters from the URL's query string."""
        # Parse the URL
        parts = urlparse(url)
        
        # Parse query parameters
        query_params = dict(parse_qsl(parts.query))
        
        # Remove specified parameters
        for key in params:
            if key in query_params:
                del query_params[key]
        
        # Return URL with updated query string
        from urllib.parse import urlunparse
        parts_list = list(parts)
        parts_list[4] = urlencode(query_params)
        return urlunparse(parts_list)

    # Placeholder functions that return empty strings to avoid template errors
    @app.template_global()
    def get_filter_url(filter_name, operation):
        """Placeholder function since filters have been removed."""
        from flask import request, url_for
        # Return current URL as fallback
        return url_for(request.endpoint, **request.view_args)
        
    @app.template_global()
    def remove_filter_url(filter_id):
        """Placeholder function since filters have been removed."""
        from flask import request, url_for
        # Return current URL as fallback
        return url_for(request.endpoint, **request.view_args)
