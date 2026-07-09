"""Tests for align/schema.py (ALIGN-03)."""
import pytest

pytestmark = pytest.mark.xfail(reason="schema.py not yet implemented", strict=False)

# Minimal synthetic words[] for structural tests (no real audio needed)
SAMPLE_WORDS = [
    {"w": "Hello",   "start": 0.10, "end": 0.40, "speaker": 1},
    {"w": "world",   "start": 0.45, "end": 0.70, "speaker": 1},
    {"w": "This",    "start": 0.80, "end": 1.00, "speaker": 1},
    {"w": "is",      "start": 1.05, "end": 1.15, "speaker": 1},
    {"w": "a",       "start": 1.18, "end": 1.22, "speaker": 1},
    {"w": "test",    "start": 1.25, "end": 1.50, "speaker": 1},
]
SAMPLE_SPOKEN = "Hello world. This is a test."

def test_timeline_schema_valid(synthetic_wav):
    """ALIGN-03: build_timeline() returns dict with all required top-level keys."""
    from align.schema import build_timeline
    tl = build_timeline(
        words=SAMPLE_WORDS,
        spoken_text=SAMPLE_SPOKEN,
        wav_path=synthetic_wav,
        align_method="whisperx-forced",
        wer_score=0.02,
    )
    required_top = {"audio", "words", "sentences", "meta"}
    assert required_top.issubset(tl.keys()), f"Missing keys: {required_top - tl.keys()}"
    assert "path" in tl["audio"]
    assert "sampleRate" in tl["audio"]
    assert "durationSec" in tl["audio"]
    assert "wer" in tl["meta"]
    assert "alignMethod" in tl["meta"]

def test_word_range_covers_all(synthetic_wav):
    """ALIGN-03: wordRanges in sentences[] are contiguous and cover every word."""
    from align.schema import build_timeline
    tl = build_timeline(
        words=SAMPLE_WORDS,
        spoken_text=SAMPLE_SPOKEN,
        wav_path=synthetic_wav,
        align_method="whisperx-forced",
        wer_score=0.02,
    )
    sentences = tl["sentences"]
    covered = set()
    for s in sentences:
        lo, hi = s["wordRange"]  # half-open [lo, hi)
        covered.update(range(lo, hi))
    assert covered == set(range(len(SAMPLE_WORDS))), \
        f"wordRanges don't cover all words. Covered: {sorted(covered)}"

def test_duration_from_audio_not_words(synthetic_wav):
    """ALIGN-03: durationSec comes from librosa.get_duration(), not words[-1].end."""
    import librosa
    from align.schema import build_timeline
    real_duration = librosa.get_duration(path=synthetic_wav)
    tl = build_timeline(
        words=SAMPLE_WORDS,
        spoken_text=SAMPLE_SPOKEN,
        wav_path=synthetic_wav,
        align_method="whisperx-forced",
        wer_score=0.02,
    )
    # The WAV is 2.0s; SAMPLE_WORDS end at 1.5s — they must differ
    assert abs(tl["audio"]["durationSec"] - real_duration) < 0.01, \
        f"durationSec {tl['audio']['durationSec']} != librosa duration {real_duration}"
    assert tl["audio"]["durationSec"] > SAMPLE_WORDS[-1]["end"], \
        "durationSec must not be derived from last word end (real audio is always longer)"
