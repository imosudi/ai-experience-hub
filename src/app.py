import os
from flask import Flask, render_template, jsonify, request
from src.config import config_by_name
from src.logger import setup_logger, logger
from src.security import csrf, limiter, setup_security_headers
from src.services.ai_service import ai_service
from src.errors import MuseSparkError
from flask_caching import Cache

# Initialize global cache
cache = Cache()

def create_app(config_name=None):
    """
    Application factory pattern. Configures logging, security, caching,
    routes, and error mappings.
    """
    if config_name is None:
        config_name = os.getenv("APP_ENV", "development")

    app = Flask(__name__, template_folder="templates")
    
    # Load configuration
    config_class = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(config_class)

    # Setup Structured Logging
    log_level = "DEBUG" if app.config.get("DEBUG") else "INFO"
    setup_logger(log_level=log_level)
    logger.info(f"Starting Muse Spark Explorer in {config_name} environment.")

    # Create static assets subdirectories
    for path in [app.config.get("UPLOAD_FOLDER"), app.config.get("GENERATED_FOLDER")]:
        if path and not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created application directory: {path}")

    # Initialize Security Extensions
    csrf.init_app(app)
    limiter.init_app(app)
    setup_security_headers(app)

    # Initialize Caching
    cache.init_app(app)

    # Initialize AI Services
    ai_service.init_app(app)

    # Register Blueprints
    from src.auth import auth_bp
    from src.views.main import main_bp
    from src.views.chat import chat_bp
    from src.views.vision import vision_bp
    from src.views.image_gen import image_gen_bp
    from src.views.agent import agent_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(vision_bp)
    app.register_blueprint(image_gen_bp)
    app.register_blueprint(agent_bp)

    # Request interceptor logging
    @app.before_request
    def log_incoming_request():
        logger.debug(f"Incoming {request.method} request to path: {request.path} (Remote IP: {request.remote_addr})")

    # ==========================================
    # Global Error Handling Configuration
    # ==========================================

    @app.errorhandler(400)
    def bad_request(error):
        msg = "The server cannot process the request due to invalid input syntax."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api') or '/stream' in request.path:
            return jsonify({"error": msg}), 400
        return render_template('base.html'), 400  # Fallback or general page

    @app.errorhandler(403)
    def forbidden(error):
        msg = "Access forbidden. CSRF verification or authorization check failed."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api') or '/stream' in request.path:
            return jsonify({"error": msg}), 403
        return render_template('base.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        msg = "The requested resource could not be found on the server."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api') or '/stream' in request.path:
            return jsonify({"error": msg}), 404
        # Redirect authenticated users to dashboard, unauthenticated to login
        return render_template('base.html'), 404

    @app.errorhandler(429)
    def rate_limit_handler(e):
        msg = f"Too many requests. Rate limit exceeded: {e.description}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api') or '/stream' in request.path:
            return jsonify({"error": msg}), 429
        return render_template('base.html'), 429

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Internal server error: {error}")
        msg = "An unexpected server error occurred. Please try again later."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api') or '/stream' in request.path:
            return jsonify({"error": msg}), 500
        return render_template('base.html'), 500

    @app.errorhandler(MuseSparkError)
    def handle_sdk_exception(error):
        logger.error(f"Custom Muse Spark SDK Exception handled: {error.message} (status: {error.status_code})")
        return jsonify(error.to_dict()), error.status_code

    return app
