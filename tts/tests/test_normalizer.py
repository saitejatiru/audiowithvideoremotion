"""RED stubs for tts.normalizer — covers AUDIO-04.

Entire module is skipped on Windows because nemo-text-processing / pynini
has no Windows wheel. Tests are still collected (skipif, not importorskip)
so the suite counts them.
"""
import platform
import pytest

pytestmark = pytest.mark.skipif(
    platform.system() == "Windows",
    reason="nemo-text-processing requires Linux (pynini has no Windows wheel)",
)


def test_currency_expanded():
    """AUDIO-04: Currency symbols are expanded to spoken words (no '$' or bare digits)."""
    from tts.normalizer import normalize  # noqa: F401 — ImportError = RED on Linux
    pytest.fail("not implemented")


def test_short_input_rejected():
    """AUDIO-04: normalize() raises ValueError for inputs below minimum length."""
    from tts.normalizer import normalize  # noqa: F401
    pytest.fail("not implemented")


def test_word_map_populated():
    """AUDIO-04: normalize() returns word_map list with 'raw', 'spoken', 'start_word' keys."""
    from tts.normalizer import normalize  # noqa: F401
    pytest.fail("not implemented")


def test_no_digits_in_spoken():
    """AUDIO-04: normalize() leaves no bare digit tokens in spoken_text."""
    from tts.normalizer import normalize  # noqa: F401
    pytest.fail("not implemented")
