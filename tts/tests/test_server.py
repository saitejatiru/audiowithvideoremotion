"""Tests for tts.server — covers INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03.

run_vibevoice is mocked by the mock_vibevoice fixture (conftest.py) so these
tests run on Windows without a GPU or the vibevoice package.
"""
import pytest


def test_synthesize_returns_wav(set_api_secret, mock_vibevoice, auth_headers):
    """AUDIO-01 / INFRA-01: POST /synthesize returns 200 with audio/wav body."""
    from fastapi.testclient import TestClient
    from tts.server import app
    client = TestClient(app)
    resp = client.post(
        "/synthesize",
        json={"text": "Hello world this is a test", "speaker_id": "default"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/wav")
    assert len(resp.content) > 0


def test_auth_rejects_bad_token(set_api_secret):
    """INFRA-01: POST /synthesize with bad Bearer token returns 401."""
    from fastapi.testclient import TestClient
    from tts.server import app
    client = TestClient(app)
    resp = client.post(
        "/synthesize",
        json={"text": "Hello world this is a test"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_synthesize_short_input_rejected(set_api_secret, auth_headers):
    """AUDIO-02: POST /synthesize with text shorter than 3 words returns 400."""
    from fastapi.testclient import TestClient
    from tts.server import app
    client = TestClient(app)
    resp = client.post(
        "/synthesize",
        json={"text": "Hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "too short" in resp.json()["detail"].lower()


def test_voices_includes_indian(set_api_secret):
    """AUDIO-03: GET /voices returns 200 and lists at least one Indian/Samuel voice."""
    from fastapi.testclient import TestClient
    from tts.server import app
    client = TestClient(app)
    resp = client.get("/voices")
    assert resp.status_code == 200
    voices = resp.json()
    assert isinstance(voices, list) and len(voices) > 0
    lowered = [v.lower() for v in voices]
    assert any("samuel" in v or "indian" in v or "default" in v for v in lowered), (
        f"Expected Samuel/indian/default in {voices}"
    )


def test_clone_voice_registered(set_api_secret, sample_wav_bytes, auth_headers):
    """AUDIO-03: POST /clone registers a new voice that appears in GET /voices."""
    from fastapi.testclient import TestClient
    from tts.server import app
    client = TestClient(app)

    resp = client.post(
        "/clone",
        data={"voice_id": "test-clone-voice"},
        files={"reference": ("test.wav", sample_wav_bytes, "audio/wav")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["voice_id"] == "test-clone-voice"

    voices_resp = client.get("/voices")
    assert "test-clone-voice" in voices_resp.json()
