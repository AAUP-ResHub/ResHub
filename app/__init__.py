from flask import Flask


def create_app(config_object=None):
    app = Flask(__name__)
    if config_object:
        app.config.update(config_object)

    # Register blueprints
    from .main import main_bp
    app.register_blueprint(main_bp)

    # TODO: Person-1 will add auth blueprint here

    # Context processor for template variables
    @app.context_processor
    def inject_year():
        from datetime import datetime, timezone
        return dict(current_year=datetime.now(timezone.utc).year)

    return app
