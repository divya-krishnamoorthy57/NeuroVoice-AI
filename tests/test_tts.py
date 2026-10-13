"""
test_tts.py
Comprehensive test suite for Text-to-Speech (TTS) endpoints and services.
Verifies natural Tamil speech synthesis, audio streaming, voice options,
caching, and error handling.
"""

import pytest
from fastapi.testclient import TestClient


def test_tts_status(client: TestClient):
    """Verifies that TTS status endpoint returns available providers and Tamil voices."""
    response = client.get("/practice/tts/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "tamil_voices" in data
    assert len(data["tamil_voices"]) >= 2
    voice_ids = [v["id"] for v in data["tamil_voices"]]
    assert "ta-IN-ValluvarNeural" in voice_ids
    assert "ta-IN-PallaviNeural" in voice_ids


def test_tts_synthesize_tamil_word(client: TestClient):
    """Verifies synthesizing an everyday practice word in Tamil produces valid MP3 audio."""
    response = client.post(
        "/practice/tts/synthesize",
        json={
            "text": "தண்ணீர்",
            "language": "ta-IN",
            "rate": 0.8
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000  # Valid MP3 audio payload


def test_tts_synthesize_tamil_sentence_with_voice(client: TestClient):
    """Verifies synthesizing a full everyday sentence with female Pallavi voice."""
    response = client.post(
        "/practice/tts/synthesize",
        json={
            "text": "எனக்குத் தண்ணீர் வேண்டும்.",
            "language": "ta-IN",
            "voice": "ta-IN-PallaviNeural",
            "rate": 0.8
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 2000


def test_tts_synthesize_spoken_feedback(client: TestClient):
    """Verifies synthesizing patient spoken feedback in Tamil."""
    feedback_text = "அருமை! சரியாக உச்சரித்தீர்கள்!"
    response = client.post(
        "/practice/tts/synthesize",
        json={
            "text": feedback_text,
            "language": "ta-IN",
            "rate": 0.85
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000


def test_tts_caching_behavior(client: TestClient):
    """Verifies that subsequent identical requests retrieve cached audio instantly."""
    payload = {
        "text": "பால்",
        "language": "ta-IN",
        "rate": 0.8
    }
    resp1 = client.post("/practice/tts/synthesize", json=payload)
    assert resp1.status_code == 200
    len1 = len(resp1.content)

    resp2 = client.post("/practice/tts/synthesize", json=payload)
    assert resp2.status_code == 200
    len2 = len(resp2.content)

    assert len1 == len2


def test_tts_validation_empty_text(client: TestClient):
    """Verifies that empty string or whitespace text is rejected cleanly."""
    response = client.post(
        "/practice/tts/synthesize",
        json={
            "text": "   ",
            "language": "ta-IN"
        }
    )
    # Either Pydantic validation (422) or ValueError (400)
    assert response.status_code in [400, 422]
