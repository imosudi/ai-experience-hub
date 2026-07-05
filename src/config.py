import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-default-38af7c9819cd")
    
    MUSE_SPARK_API_KEY = os.getenv("MUSE_SPARK_API_KEY", "demo")
    MUSE_SPARK_BASE_URL = os.getenv("MUSE_SPARK_BASE_URL", "http://localhost:8000")
    
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    
    # Parse upload size, default to 5MB (5 * 1024 * 1024)
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 5242880))
    # Flask-specific property for max content length
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE
    
    DEMO_TOKEN = os.getenv("DEMO_TOKEN", "MUSE-SPARK-DEMO-2026")
    
    # Rate Limiting default
    RATELIMIT_DEFAULT = "60 per minute"
    RATELIMIT_STORAGE_URI = "memory://"
    
    # Caching config
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    # Custom folders
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static", "uploads")
    GENERATED_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static", "generated")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    APP_ENV = "development"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    APP_ENV = "production"
    # In production, we might override caching or session cookies security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    APP_ENV = "testing"
    # Ensure CSRF is disabled in test suite to facilitate form submissions
    WTF_CSRF_ENABLED = False
    MUSE_SPARK_API_KEY = "demo"
    # Keep upload/generated folders separate for tests if needed
    UPLOAD_FOLDER = "/tmp/muse_tests/uploads"
    GENERATED_FOLDER = "/tmp/muse_tests/generated"


# Configuration dictionary mapping
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}
