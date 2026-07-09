"""Tests for tts.normalizer — covers AUDIO-04.

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
    from tts.normalizer import normalize
    spoken, word_map = normalize("I owe $42.50 today")
    assert "$" not in spoken, "Dollar sign must not appear in spoken text"
    assert not any(t.isdigit() for t in spoken.split()), "No digit-only tokens allowed"
    assert any(e["raw"] == "$42.50" for e in word_map), "word_map must record '$42.50' entry"


def test_short_input_rejected():
    """AUDIO-04: normalize() raises ValueError for inputs below minimum length."""
    from tts.normalizer import normalize
    with pytest.raises(ValueError, match="minimum 3"):
        normalize("ok")
    with pytest.raises(ValueError, match="minimum 3"):
        normalize("two words")


def test_word_map_populated():
    """AUDIO-04: normalize() returns word_map list with 'raw', 'spoken', 'start_word' keys."""
    from tts.normalizer import normalize
    _, word_map = normalize("Pay 25% service charge")
    assert len(word_map) >= 1, "word_map must have at least one entry for '25%'"
    for entry in word_map:
        assert set(entry.keys()) == {"raw", "spoken", "start_word"}, (
            f"word_map entry has wrong keys: {set(entry.keys())}"
        )
        assert isinstance(entry["start_word"], int)


def test_no_digits_in_spoken():
    """AUDIO-04: normalize() leaves no bare digit tokens in spoken_text."""
    from tts.normalizer import normalize
    spoken, _ = normalize("I owe $42.50 and 25% extra")
    digit_tokens = [t for t in spoken.split() if t.isdigit()]
    assert digit_tokens == [], f"Digit-only tokens found in spoken text: {digit_tokens}"
