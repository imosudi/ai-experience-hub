import io
import pytest
from PIL import Image

def create_dummy_image(format="PNG"):
    """Helper to create dummy image in memory for uploading tests."""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=format)
    img_byte_arr.seek(0)
    return img_byte_arr


def test_vision_page_renders(auth_client):
    """Verifies that the vision page renders successfully."""
    response = auth_client.get('/vision')
    assert response.status_code == 200
    assert b"Vision Analysis" in response.data
    assert b"Image File Upload" in response.data


def test_vision_upload_no_file(auth_client):
    """Verifies that posting without a file returns 400."""
    response = auth_client.post('/vision/upload')
    assert response.status_code == 400
    assert b"No file uploaded" in response.data


def test_vision_upload_invalid_format(auth_client):
    """Verifies that posting unsupported file formats fails."""
    data = {
        'file': (io.BytesIO(b"not-an-image-content"), 'test.txt')
    }
    response = auth_client.post('/vision/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Unsupported file format" in response.data


def test_vision_upload_success(auth_client):
    """Verifies that uploading a valid image returns a successful JSON analysis payload."""
    img_data = create_dummy_image("PNG")
    data = {
        'file': (img_data, 'test_pet_dog.png')
    }
    response = auth_client.post('/vision/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    
    res_json = response.json
    assert "description" in res_json
    assert "detected_objects" in res_json
    assert "ocr_text" in res_json
    assert "metadata" in res_json
    assert res_json["metadata"]["width"] == 100
    assert res_json["metadata"]["height"] == 100
    assert res_json["metadata"]["format"] == "PNG"
