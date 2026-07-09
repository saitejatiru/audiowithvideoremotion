"""
Tests for align/align_pipeline.py — orchestration routing (ALIGN-01..04).

All heavy calls (align_known_transcript, check_wer, fallback_align, build_timeline,
write_timeline) are monkeypatched so these run GREEN on Windows without GPU or models.

Routes tested:
  1. forced-ok:      primary → low NaN → WER ok   → whisperx-forced timeline
  2. drift:          primary → low NaN → WER regen → AlignmentDriftError
  3. struct-fail:    primary → high NaN            → fallback path
  4. use_fallback:   use_fallback=True             → fallback path directly
"""
import pytest
from unittest.mock import patch, MagicMock

# ── shared stubs ──────────────────────────────────────────────────────────────

_WORDS_GOOD = [
    {"w": "Hello", "start": 0.1, "end": 0.4, "speaker": 1},
    {"w": "world", "start": 0.5, "end": 0.8, "speaker": 1},
]

_WORDS_NAN = [
    {"w": "Hello", "start": float("nan"), "end": float("nan"), "speaker": 1},
    {"w": "world", "start": float("nan"), "end": float("nan"), "speaker": 1},
    {"w": "test",  "start": float("nan"), "end": float("nan"), "speaker": 1},
]

_TIMELINE_FORCED = {
    "audio":     {"path": "x.wav", "sampleRate": 16000, "durationSec": 2.0},
    "words":     _WORDS_GOOD,
    "sentences": [],
    "scenes":    [],
    "meta":      {"alignMethod": "whisperx-forced", "wer": 0.02, "generator": "vibevoice"},
}

_TIMELINE_FALLBACK = {
    "audio":     {"path": "x.wav", "sampleRate": 16000, "durationSec": 2.0},
    "words":     _WORDS_GOOD,
    "sentences": [],
    "scenes":    [],
    "meta":      {"alignMethod": "whisper-timestamped-fallback", "wer": 0.0, "generator": "vibevoice"},
}


# ── tests ─────────────────────────────────────────────────────────────────────

def test_forced_ok_returns_whisperx_timeline():
    """Route: primary alignment → low NaN ratio → WER ok → whisperx-forced."""
    from align.align_pipeline import run_alignment

    with (
        patch("align.align_pipeline.align_known_transcript", return_value={"words": _WORDS_GOOD}),
        patch("align.align_pipeline.nan_ratio", return_value=0.0),
        patch("align.align_pipeline.check_wer",  return_value=("ok", 0.02)),
        patch("align.align_pipeline.build_timeline", return_value=_TIMELINE_FORCED),
        patch("align.align_pipeline.write_timeline") as mock_write,
    ):
        result = run_alignment("x.wav", "Hello world.", output_path="out.json")

    assert result["meta"]["alignMethod"] == "whisperx-forced"
    assert result["meta"]["wer"] == 0.02
    mock_write.assert_called_once_with(_TIMELINE_FORCED, "out.json")


def test_drift_raises_alignment_drift_error():
    """Route: primary → low NaN → WER regenerate → AlignmentDriftError raised."""
    from align.align_pipeline import run_alignment, AlignmentDriftError

    with (
        patch("align.align_pipeline.align_known_transcript", return_value={"words": _WORDS_GOOD}),
        patch("align.align_pipeline.nan_ratio",  return_value=0.0),
        patch("align.align_pipeline.check_wer",  return_value=("regenerate", 0.25)),
        patch("align.align_pipeline.build_timeline"),
        patch("align.align_pipeline.write_timeline"),
    ):
        with pytest.raises(AlignmentDriftError) as exc_info:
            run_alignment("x.wav", "Hello world.", output_path="out.json")

    assert exc_info.value.wer_score == pytest.approx(0.25)


def test_structural_failure_triggers_fallback():
    """Route: primary → high NaN ratio → fallback path (no WER check)."""
    from align.align_pipeline import run_alignment

    with (
        patch("align.align_pipeline.align_known_transcript", return_value={"words": _WORDS_NAN}),
        patch("align.align_pipeline.nan_ratio",  return_value=1.0),   # all NaN
        patch("align.align_pipeline.check_wer")  as mock_wer,
        patch("align.align_pipeline.fallback_align", return_value=_WORDS_GOOD),
        patch("align.align_pipeline.build_timeline", return_value=_TIMELINE_FALLBACK),
        patch("align.align_pipeline.write_timeline"),
    ):
        result = run_alignment("x.wav", "Hello world.", output_path="out.json")

    # WER must NOT be called on structural failure
    mock_wer.assert_not_called()
    assert result["meta"]["alignMethod"] == "whisper-timestamped-fallback"


def test_use_fallback_bypasses_primary_alignment():
    """Route: use_fallback=True → skip primary entirely, call fallback directly."""
    from align.align_pipeline import run_alignment

    with (
        patch("align.align_pipeline.align_known_transcript") as mock_primary,
        patch("align.align_pipeline.fallback_align", return_value=_WORDS_GOOD),
        patch("align.align_pipeline.build_timeline", return_value=_TIMELINE_FALLBACK),
        patch("align.align_pipeline.write_timeline") as mock_write,
    ):
        result = run_alignment("x.wav", "Hello world.", output_path="out.json", use_fallback=True)

    # Primary alignment must NOT be called when use_fallback=True
    mock_primary.assert_not_called()
    assert result["meta"]["alignMethod"] == "whisper-timestamped-fallback"
    mock_write.assert_called_once()


def test_alignment_drift_error_carries_wer_score():
    """AlignmentDriftError.wer_score is accessible for Phase 6 retry logic."""
    from align.align_pipeline import AlignmentDriftError
    err = AlignmentDriftError(0.17)
    assert err.wer_score == pytest.approx(0.17)
    assert "0.170" in str(err)
