"""Shared pytest fixtures for align/ tests."""
import os
import numpy as np
import pytest

# Known spoken text used for schema and verifier tests (no digits — wav2vec2 vocab gap)
SPOKEN_TEXT = (
    "Hello world. This is a test sentence for the alignment engine. "
    "Forced alignment produces word level timestamps."
)

@pytest.fixture(scope="session")
def synthetic_wav(tmp_path_factory):
    """
    Generate a 2-second 16kHz mono sine-wave WAV.
    Not realistic speech — used for structural/schema tests only.
    Real speech tests use TEST_CLIP_PATH env var (see below).
    """
    import soundfile as sf
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    tmp = tmp_path_factory.mktemp("audio")
    wav_path = str(tmp / "synthetic.wav")
    sf.write(wav_path, audio, sr)
    return wav_path

@pytest.fixture(scope="session")
def real_wav_path():
    """
    Path to a real speech WAV for integration tests (known-good clip).
    Set TEST_CLIP_PATH env var to a 5-30s English speech WAV.
    Tests using this fixture are skipped if the env var is not set.
    """
    path = os.environ.get("TEST_CLIP_PATH")
    if not path or not os.path.exists(path):
        pytest.skip("TEST_CLIP_PATH not set or file missing — skipping integration test")
    return path
