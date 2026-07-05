import os
import json
import pytest

def test_image_gen_page_renders(auth_client):
    """Verifies that the image generation dashboard renders."""
    response = auth_client.get('/image-gen')
    assert response.status_code == 200
    assert b"Image Generation" in response.data
    assert b"Generation Parameters" in response.data


def test_image_gen_no_prompt(auth_client):
    """Verifies that posting without a prompt returns 400."""
    response = auth_client.post('/image-gen/generate', json={
        "prompt": "",
        "style": "synthwave"
    })
    assert response.status_code == 400
    assert b"Prompt is required" in response.data


def test_image_gen_invalid_seed(auth_client):
    """Verifies that seed parameters are validated for numeric values."""
    response = auth_client.post('/image-gen/generate', json={
        "prompt": "neon cat",
        "seed": "invalid-seed"
    })
    assert response.status_code == 400


def test_image_gen_success(auth_client, app):
    """Verifies that valid parameters generate a dynamic image and save it on disk."""
    response = auth_client.post('/image-gen/generate', json={
        "prompt": "synthwave sunset grid",
        "style": "synthwave",
        "size": "512x512",
        "quality": "standard",
        "seed": 42
    })
    
    assert response.status_code == 200
    res_json = response.json
    assert res_json["success"] is True
    assert "url" in res_json
    assert res_json["seed"] == 42
    assert res_json["style"] == "synthwave"
    
    # Verify file exists on the temporary test folder disk
    # url starts with /static/generated/filename
    filename = res_json["filename"]
    filepath = os.path.join(app.config.get("GENERATED_FOLDER"), filename)
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0
    
    # Cleanup file
    try:
        os.remove(filepath)
    except OSError:
        pass
