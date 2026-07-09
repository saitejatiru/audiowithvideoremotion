"""Shared fixtures for tts test suite."""
import io
import struct
import pytest

TEST_SECRET = "test-secret-123"


@pytest.fixture
def test_secret():
    return TEST_SECRET


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_SECRET}"}


@pytest.fixture(autouse=False)
def set_api_secret(monkeypatch):
    monkeypatch.setenv("API_SECRET", TEST_SECRET)


@pytest.fixture
def mock_vibevoice(monkeypatch):
    """Patches tts.server.run_vibevoice to return 2s float32 zeros at 24kHz."""
    try:
        import numpy as np
        mock_audio = np.zeros(48000, dtype=np.float32)  # 2s at 24kHz
    except ImportError:
        mock_audio = None  # ponytail: numpy unavailable; tests fail anyway in RED state
    monkeypatch.setattr("tts.server.run_vibevoice", lambda *a, **k: mock_audio)
    return mock_audio


@pytest.fixture
def sample_wav_bytes():
    """Returns valid WAV bytes: 2s silence, 24kHz, PCM16. No soundfile dep needed."""
    sample_rate = 24000
    n_samples = sample_rate * 2   # 2 seconds
    data_size = n_samples * 2     # PCM16 = 2 bytes per sample
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    return buf.getvalue()
