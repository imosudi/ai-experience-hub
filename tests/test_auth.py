import pytest
from flask import session

def test_login_page_renders(client):
    """Verifies that the login page renders successfully."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Muse Spark Explorer" in response.data
    assert b"Verify Token" in response.data


def test_route_protection(client):
    """Verifies that protected routes redirect to login when unauthenticated."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_login_success(client, app):
    """Verifies that submitting the correct demo token starts a session."""
    demo_token = app.config.get('DEMO_TOKEN', 'MUSE-SPARK-DEMO-2026')
    # Fetch CSRF token for WTForm validation if enabled, but TestingConfig has WTF_CSRF_ENABLED=False
    response = client.post('/login', data={'token': demo_token}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome to Muse Spark Explorer" in response.data
    
    with client.session_transaction() as sess:
        assert sess.get('auth_token') == demo_token


def test_login_failure(client):
    """Verifies that submitting an incorrect token fails and shows error."""
    response = client.post('/login', data={'token': 'WRONG-TOKEN'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid authentication token" in response.data
    
    with client.session_transaction() as sess:
        assert 'auth_token' not in sess


def test_logout(auth_client):
    """Verifies that logging out terminates the session and redirects to login."""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out of your session." in response.data
    
    with auth_client.session_transaction() as sess:
        assert 'auth_token' not in sess
