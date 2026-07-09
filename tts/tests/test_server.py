"""RED stubs for tts.server — covers INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03.

Imports deferred into test bodies so tests are collected on Windows even
before tts/server.py is written (ImportError = RED, not collection error).
"""
import pytest


def test_synthesize_returns_wav(set_api_secret, mock_vibevoice, auth_headers):
    """AUDIO-01 / INFRA-01: POST /synthesize returns 200 with audio/wav body."""
    from tts.server import app  # noqa: F401 — ImportError = RED
    pytest.fail("not implemented")


def test_auth_rejects_bad_token(set_api_secret):
    """INFRA-01: POST /synthesize with bad Bearer token returns 401."""
    from tts.server import app  # noqa: F401
    pytest.fail("not implemented")


def test_synthesize_short_input_rejected(set_api_secret, auth_headers):
    """AUDIO-02: POST /synthesize with text shorter than minimum returns 400."""
    from tts.server import app  # noqa: F401
    pytest.fail("not implemented")


def test_voices_includes_indian(set_api_secret):
    """AUDIO-03: GET /voices returns 200 and lists at least one Indian voice (Samuel)."""
    from tts.server import app  # noqa: F401
    pytest.fail("not implemented")


def test_clone_voice_registered(set_api_secret, sample_wav_bytes):
    """AUDIO-03: POST /clone registers a new voice that appears in GET /voices."""
    from tts.server import app  # noqa: F401
    pytest.fail("not implemented")
