import pytest
from src.app import create_app
from src.services.ai_service import ai_service

@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for testing."""
    app = create_app("testing")
    
    # Initialize services
    with app.app_context():
        ai_service.init_app(app)
        ai_service.reset_stats()
        
    yield app


@pytest.fixture
def client(app):
    """A test client for the application."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """A test client that has already authenticated with the mock token."""
    with client.session_transaction() as sess:
        sess['auth_token'] = app.config.get('DEMO_TOKEN', 'MUSE-SPARK-DEMO-2026')
    return client
