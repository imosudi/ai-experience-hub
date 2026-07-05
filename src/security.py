from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from src.logger import logger

# Initialize CSRF Protection
csrf = CSRFProtect()

# Initialize Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60 per minute"],
    storage_uri="memory://"
)

def setup_security_headers(app):
    """
    Sets up Talisman to inject HTTP security headers: HSTS, XSS Protection,
    Clickjacking prevention, and a strict Content Security Policy.
    """
    # Strict Content Security Policy allowing local assets, Bootstrap, and Google Fonts
    csp = {
        'default-src': "'self'",
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Allowed for dynamic theme stylesheets
            "https://cdn.jsdelivr.net",  # Bootstrap stylesheet
            "https://fonts.googleapis.com"  # Google Fonts stylesheet
        ],
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Allowed for local templates UI state management
            "https://cdn.jsdelivr.net"  # Bootstrap and external libraries
        ],
        'font-src': [
            "'self'",
            "https://cdn.jsdelivr.net",  # Bootstrap Icons font file
            "https://fonts.gstatic.com"  # Google Fonts font file
        ],
        'img-src': [
            "'self'",
            "data:",  # Allowed for base64 encoded images (dynamic Pillow generation & previews)
            "https://images.unsplash.com"  # Allowed for placeholder graphics
        ],
        'connect-src': [
            "'self'"  # Allow API requests and SSE events to loopback
        ]
    }

    # Initialize Talisman
    Talisman(
        app,
        content_security_policy=csp,
        force_https=False,  # Set False for development/local demo. Change to True in production config if TLS is present.
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        frame_options='DENY',  # Block clickjacking
        referrer_policy='strict-origin-when-cross-origin'
    )
    logger.info("Security headers and CSP initialized via Talisman.")
