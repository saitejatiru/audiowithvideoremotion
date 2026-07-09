"""RED stubs for tts.schema — inter-phase contract.

Phase 2 (alignment engine) imports Timeline from tts.schema. These tests
define the exact shape of the timeline.json contract.
"""
import pytest


def test_timeline_validates(tmp_path):
    """Timeline.model_validate() succeeds for a valid minimal payload."""
    from tts.schema import Timeline  # noqa: F401 — ImportError = RED
    pytest.fail("not implemented")


def test_write_phase1_timeline_structure(tmp_path):
    """write_phase1_timeline() produces JSON with keys: audio, words, sentences, scenes, meta.

    words=[], sentences=[], scenes=[] in Phase 1 output (populated in Phase 2+).
    meta['generator'] matches the generator argument.
    """
    from tts.schema import write_phase1_timeline  # noqa: F401
    pytest.fail("not implemented")
