import json
import pytest

def test_chat_page_renders(auth_client):
    """Verifies that the chat page renders successfully for authorized sessions."""
    response = auth_client.get('/chat')
    assert response.status_code == 200
    assert b"Streaming Chat" in response.data
    assert b"Model Parameters" in response.data


def test_chat_stream_validation(auth_client):
    """Verifies that streaming chat rejects empty message lists."""
    response = auth_client.post('/chat/stream', json={
        "messages": [],
        "temperature": 0.7
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_chat_stream_invalid_params(auth_client):
    """Verifies that streaming chat validates temperatures parameter type."""
    response = auth_client.post('/chat/stream', json={
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": "not-a-float"
    })
    assert response.status_code == 400


def test_chat_stream_success(auth_client):
    """Verifies that streaming chat returns valid EventSource (SSE) data chunks."""
    response = auth_client.post('/chat/stream', json={
        "messages": [{"role": "user", "content": "Hi"}],
        "temperature": 0.7,
        "max_tokens": 10
    })
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    
    # Read first few lines of stream
    lines = response.data.decode('utf-8').split('\n\n')
    assert len(lines) > 1
    
    first_chunk = lines[0]
    assert first_chunk.startswith("data: ")
    
    # Parse JSON token
    chunk_json = json.loads(first_chunk[6:])
    assert "token" in chunk_json or "error" in chunk_json
