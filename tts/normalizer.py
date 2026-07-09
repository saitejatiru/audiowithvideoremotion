"""Text normalizer for TTS pipeline — AUDIO-04.

Output contract: spoken_text returned by normalize() is the CANONICAL spoken form.
Pass it to BOTH:
  1. POST /synthesize  (TTS input — what the model voices)
  2. whisperx.align()  (Phase 2 — wav2vec2 needs digit-free text for alignment)

The word_map bridges raw display (Phase 4 captions) to spoken alignment (Phase 2):
  word_map[i]["raw"]    → displayed verbatim in Remotion captions
  word_map[i]["spoken"] → used for wav2vec2/whisperx forced alignment

ponytail: NeMo fails on Windows (pynini no Windows wheel); guard import so module
loads cleanly on all platforms. Normalizer tests skip on Windows via pytestmark.
WeTextProcessing is a viable Windows stand-in for local dev but is NOT imported here —
keep it in your dev environment; do not add it to production code.
"""
import logging
import re

# ponytail: NeMo/pynini has no Windows wheel; guard so module imports on all platforms.
# On Windows, _normalizer is None and normalize() returns (raw_text, []) with a warning.
# Tests skip on Windows via pytestmark — see tts/tests/test_normalizer.py.
try:
    from nemo_text_processing.text_normalization.normalize import Normalizer as _NeMoNorm
    _normalizer = _NeMoNorm(input_case="cased", lang="en")
except ImportError:
    _normalizer = None

_log = logging.getLogger(__name__)

# Semiotic span regex — from 01-RESEARCH.md Pattern 3.
# Ordered most-specific first to avoid partial shadowing.
_SPAN_RE = re.compile(
    r"\$[\d,]+(?:\.\d+)?"               # currency: $42.50
    r"|(?:\d+(?:,\d{3})*(?:\.\d+)?%)"  # percentage: 25%
    r"|(?:\b\d{1,2}/\d{1,2}/\d{2,4}\b)"  # date: 4/7/2026
    r"|(?:https?://\S+)"                  # URL
    r"|(?:\b\d+(?:st|nd|rd|th)\b)"        # ordinal: 3rd
    r"|(?:\b[\d,]+(?:\.\d+)?\b)"          # bare number: 42, 1,000, 3.14
)


def normalize(raw_text: str) -> tuple[str, list[dict]]:
    """Return (spoken_text, word_map).

    spoken_text: raw_text with numbers/currency/symbols expanded to spoken words.
                 No digit-only tokens remain — wav2vec2 alignment constraint satisfied.
    word_map:    list of {"raw": str, "spoken": str, "start_word": int} for every
                 token that was changed. Phase 4 uses raw for display, spoken for
                 alignment.

    Raises ValueError if input has fewer than 3 words.
    """
    words = raw_text.split()
    if len(words) < 3:
        raise ValueError(f"Input too short: {len(words)} words (minimum 3)")

    if _normalizer is None:
        _log.warning(
            "nemo-text-processing not available (Windows/missing install); "
            "returning raw text unchanged. Run on Linux/Colab for full normalization."
        )
        return raw_text, []

    word_map: list[dict] = []
    spoken_tokens: list[str] = []
    for w_idx, token in enumerate(words):
        stripped = token.strip(".,;:!?")
        if _SPAN_RE.fullmatch(stripped):
            spoken_form = _normalizer.normalize(token, verbose=False)
            if spoken_form != token:
                word_map.append({
                    "raw": token,
                    "spoken": spoken_form,
                    "start_word": w_idx,
                })
                spoken_tokens.append(spoken_form)
                continue
        spoken_tokens.append(token)

    return " ".join(spoken_tokens), word_map
