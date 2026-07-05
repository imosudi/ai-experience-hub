import pytest
from src.sdk.client import MuseSpark, MuseSparkChunk, MuseSparkResponse
from src.errors import InvalidInputError

def test_sdk_initialization():
    """Verifies that the SDK client configures properly."""
    sdk = MuseSpark(api_key="demo", base_url="http://localhost:8080")
    assert sdk.api_key == "demo"
    assert sdk.base_url == "http://localhost:8080"
    assert sdk.is_demo is True


def test_sdk_chat_validation():
    """Verifies that the SDK validates temperature bounds and token counts."""
    sdk = MuseSpark(api_key="demo")
    with pytest.raises(InvalidInputError):
        sdk.chat(messages=[{"role": "user", "content": "hi"}], temperature=-0.5)
        
    with pytest.raises(InvalidInputError):
        sdk.chat(messages=[{"role": "user", "content": "hi"}], temperature=2.5)

    with pytest.raises(InvalidInputError):
        sdk.chat(messages=[{"role": "user", "content": "hi"}], max_tokens=-10)


def test_sdk_chat_completions_simulated_stream():
    """Verifies that the simulated chat completions returns a stream generator."""
    sdk = MuseSpark(api_key="demo")
    chunks = list(sdk.chat(messages=[{"role": "user", "content": "hello"}], stream=True))
    
    assert len(chunks) > 0
    assert isinstance(chunks[0], MuseSparkChunk)
    assert any(c.is_final for c in chunks)
    
    # Check that it generated some content
    full_text = "".join([c.content for c in chunks if not c.is_final])
    assert "Hello!" in full_text or "multimodal" in full_text


def test_sdk_chat_completions_simulated_non_stream():
    """Verifies that the simulated chat completions returns standard response wrapper."""
    sdk = MuseSpark(api_key="demo")
    response = sdk.chat(messages=[{"role": "user", "content": "hello"}], stream=False)
    
    assert isinstance(response, MuseSparkResponse)
    assert "Hello!" in response.content
    assert response.usage["prompt_tokens"] > 0
    assert response.latency > 0


def test_sdk_vision_simulated():
    """Verifies that the simulated vision analyzer returns description and objects."""
    sdk = MuseSpark(api_key="demo")
    dummy_bytes = b"dummy-image-data-png"
    response = sdk.vision_analyze(dummy_bytes, "test.png", "image/png")
    
    assert isinstance(response, MuseSparkResponse)
    assert "description" in response.content
    assert "detected_objects" in response.content
    assert "ocr_text" in response.content
    assert response.content["metadata"]["filename"] == "test.png"


def test_sdk_image_generation_simulated():
    """Verifies that the simulated image generator returns PNG image bytes."""
    sdk = MuseSpark(api_key="demo")
    response = sdk.generate_image(prompt="synthwave sunset", style="synthwave", seed=42)
    
    assert isinstance(response, MuseSparkResponse)
    assert "image_bytes" in response.content
    assert response.content["format"] == "PNG"
    assert response.content["seed"] == 42
    assert response.content["style"] == "synthwave"
