"""Shared pytest fixtures for storyboard/ tests."""
import pytest


# --- Sample data matching align/schema.py output format ---

SAMPLE_SENTENCES = [
    {
        "idx": 0,
        "text": "Hello world.",
        "start": 0.0,
        "end": 1.2,
        "speaker": 1,
        "wordRange": [0, 2],
    },
    {
        "idx": 1,
        "text": "This is a test sentence.",
        "start": 1.2,
        "end": 3.5,
        "speaker": 1,
        "wordRange": [2, 7],
    },
    {
        "idx": 2,
        "text": "Forced alignment produces timestamps.",
        "start": 3.5,
        "end": 5.8,
        "speaker": 1,
        "wordRange": [7, 11],
    },
]


SAMPLE_TIMELINE = {
    "audio": {
        "path": "test.wav",
        "sampleRate": 24000,
        "durationSec": 6.0,
    },
    "words": [
        {"w": "Hello", "start": 0.0, "end": 0.5, "speaker": 1},
        {"w": "world.", "start": 0.5, "end": 1.2, "speaker": 1},
        {"w": "This", "start": 1.2, "end": 1.5, "speaker": 1},
        {"w": "is", "start": 1.5, "end": 1.7, "speaker": 1},
        {"w": "a", "start": 1.7, "end": 1.8, "speaker": 1},
        {"w": "test", "start": 1.8, "end": 2.2, "speaker": 1},
        {"w": "sentence.", "start": 2.2, "end": 3.5, "speaker": 1},
        {"w": "Forced", "start": 3.5, "end": 3.9, "speaker": 1},
        {"w": "alignment", "start": 3.9, "end": 4.5, "speaker": 1},
        {"w": "produces", "start": 4.5, "end": 5.1, "speaker": 1},
        {"w": "timestamps.", "start": 5.1, "end": 5.8, "speaker": 1},
    ],
    "sentences": SAMPLE_SENTENCES,
    "scenes": [],
    "meta": {
        "lang": "en",
        "wer": 0.05,
        "generator": "vibevoice",
        "alignMethod": "whisperx-forced",
        "alignedAt": "2026-07-09T00:00:00+00:00",
    },
}


@pytest.fixture
def sample_sentences():
    """Return a deep copy of sample sentences to prevent cross-test mutation."""
    import copy
    return copy.deepcopy(SAMPLE_SENTENCES)


@pytest.fixture
def sample_timeline():
    """Return a deep copy of sample timeline to prevent cross-test mutation."""
    import copy
    return copy.deepcopy(SAMPLE_TIMELINE)
