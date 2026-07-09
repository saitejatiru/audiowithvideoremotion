"""Tests for tts.voice_store — covers AUDIO-05."""
import os
import pytest


def test_default_indian_voice_exists():
    """AUDIO-05: voice_store.get_voice_path('default') returns a path that exists on disk."""
    from tts.voice_store import get_voice_path
    path = get_voice_path("default")
    assert os.path.exists(path), f"default voice path does not exist: {path}"


def test_list_voices_nonempty():
    """AUDIO-05: voice_store.list_voice_ids() returns a non-empty list."""
    from tts.voice_store import list_voice_ids
    ids = list_voice_ids()
    assert len(ids) > 0


def test_list_voices_includes_default():
    """AUDIO-05: 'default' or 'samuel' (case-insensitive) appears in voice list."""
    from tts.voice_store import list_voice_ids
    ids = list_voice_ids()
    lowered = [v.lower() for v in ids]
    assert any("default" in v or "samuel" in v for v in lowered), (
        f"Expected 'default' or 'samuel' in {ids}"
    )
