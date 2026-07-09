"""Tests for align/verifier.py (ALIGN-02)."""
import pytest

pytestmark = pytest.mark.xfail(reason="verifier.py not yet implemented", strict=False)

def test_wer_known_good(real_wav_path):
    """ALIGN-02: WER < 0.08 on a known-good clip."""
    from align.verifier import compute_wer
    from align.tests.conftest import SPOKEN_TEXT
    score = compute_wer(SPOKEN_TEXT, real_wav_path)
    assert 0.0 <= score <= 1.0
    assert score < 0.08, f"WER {score:.3f} exceeds threshold on known-good clip"

def test_wer_drift_detected(real_wav_path):
    """ALIGN-02: WER > threshold when reference is deliberately wrong."""
    from align.verifier import compute_wer
    # Completely wrong reference → WER should be > threshold
    wrong_reference = "the quick brown fox jumps over the lazy dog"
    score = compute_wer(wrong_reference, real_wav_path)
    assert score > 0.08, f"WER {score:.3f} should be high for a wrong reference"

def test_check_wer_returns_tuple(real_wav_path):
    """ALIGN-02: check_wer() returns (decision_str, float) tuple."""
    from align.verifier import check_wer
    from align.tests.conftest import SPOKEN_TEXT
    decision, score = check_wer(SPOKEN_TEXT, real_wav_path)
    assert decision in ("ok", "regenerate", "fallback")
    assert isinstance(score, float)
