"""RED stubs for tts.voice_store — covers AUDIO-05."""
import pytest


def test_default_indian_voice_exists():
    """AUDIO-05: voice_store.get_voice_path('default') returns a path that exists on disk."""
    from tts import voice_store  # noqa: F401 — ImportError = RED
    pytest.fail("not implemented")


def test_list_voices_nonempty():
    """AUDIO-05: voice_store.list_voice_ids() returns a non-empty list."""
    from tts import voice_store  # noqa: F401
    pytest.fail("not implemented")


def test_list_voices_includes_default():
    """AUDIO-05: 'default' or 'samuel' (case-insensitive) appears in voice list."""
    from tts import voice_store  # noqa: F401
    pytest.fail("not implemented")
