import pytest
from unittest.mock import patch
from src.services.agent_service import agent_service
from src.errors import InvalidInputError

def test_agent_page_renders(auth_client):
    """Verifies that the webpage summarizer page renders."""
    response = auth_client.get('/agent')
    assert response.status_code == 200
    assert b"Webpage Summarizer Agent" in response.data


def test_agent_no_url(auth_client):
    """Verifies that running the agent without a URL fails."""
    response = auth_client.post('/agent/run', json={"url": ""})
    assert response.status_code == 400
    assert b"URL is required" in response.data


def test_agent_ssrf_blocking_localhost(auth_client):
    """Verifies that SSRF protection blocks localhost loopback URLs."""
    response = auth_client.post('/agent/run', json={"url": "http://127.0.0.1:8000/admin"})
    assert response.status_code == 400
    assert b"restricted" in response.data or b"validation failed" in response.data


def test_agent_ssrf_blocking_private_subnet(auth_client):
    """Verifies that SSRF protection blocks private subnets (e.g. 192.168.1.1)."""
    response = auth_client.post('/agent/run', json={"url": "http://192.168.1.1/secret"})
    assert response.status_code == 400
    assert b"restricted" in response.data or b"validation failed" in response.data


@patch('src.services.agent_service.AgentService.fetch_and_clean_webpage')
def test_agent_run_success(mock_fetch, auth_client):
    """Verifies that the agent scrapes and summarizes target web documents successfully."""
    # Set mock response for downloaded page content
    mock_fetch.return_value = {
        "title": "Test AI Breakthrough",
        "clean_text": "Meta AI Superintelligence Labs announced a massive breakthrough in native visual reasoning models named Muse Spark. The model showcases multimodality capabilities.",
        "word_count": 22,
        "reading_time": 1
    }

    response = auth_client.post('/agent/run', json={"url": "https://example.com/breakthrough"})
    
    assert response.status_code == 200
    res_json = response.json
    assert res_json["title"] == "Test AI Breakthrough"
    assert "summary" in res_json
    assert "key_points" in res_json
    assert "action_items" in res_json
    assert res_json["word_count"] == 22
    assert res_json["reading_time"] == 1
