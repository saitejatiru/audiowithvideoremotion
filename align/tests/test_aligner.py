"""Tests for align/aligner.py (ALIGN-01) and align/fallback.py (ALIGN-04)."""
import pytest
import math

pytestmark = pytest.mark.xfail(reason="aligner.py not yet implemented", strict=False)

def test_words_have_timestamps(real_wav_path):
    """ALIGN-01: every returned word has non-NaN start and end."""
    from align.aligner import align_known_transcript
    from align.tests.conftest import SPOKEN_TEXT
    result = align_known_transcript(real_wav_path, SPOKEN_TEXT)
    words = result["words"]
    assert len(words) > 0
    for w in words:
        assert w["start"] is not None and not math.isnan(w["start"]), f"NaN start: {w}"
        assert w["end"]   is not None and not math.isnan(w["end"]),   f"NaN end: {w}"

def test_word_timestamps_monotonic(real_wav_path):
    """ALIGN-01: word timestamps are monotonically non-decreasing."""
    from align.aligner import align_known_transcript
    from align.tests.conftest import SPOKEN_TEXT
    result = align_known_transcript(real_wav_path, SPOKEN_TEXT)
    words = result["words"]
    for i in range(1, len(words)):
        assert words[i]["start"] >= words[i-1]["start"], \
            f"Non-monotonic at {i}: {words[i-1]} -> {words[i]}"

def test_fallback_schema_matches_primary(real_wav_path):
    """ALIGN-04: fallback_align() returns same words[] shape as primary path."""
    from align.fallback import fallback_align
    words = fallback_align(real_wav_path)
    assert len(words) > 0
    required_keys = {"w", "start", "end", "speaker"}
    for w in words:
        assert required_keys.issubset(w.keys()), f"Missing keys in fallback word: {w}"
        assert isinstance(w["w"], str)
        assert isinstance(w["start"], float)
        assert isinstance(w["end"], float)
        assert isinstance(w["speaker"], int)
