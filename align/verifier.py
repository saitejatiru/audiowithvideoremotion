"""
align/verifier.py — ASR-WER guard (ALIGN-02).

Contract:
  compute_wer(reference_spoken, audio_path) → float [0.0, 1.0]
  check_wer(reference_spoken, audio_path)   → tuple[str, float]
    str is one of: "ok" | "regenerate"

CRITICAL: BOTH reference and hypothesis are normalized with EnglishTextNormalizer
before WER computation. Without this, digit strings ("50%") vs. spoken forms
("fifty percent") inflate WER and cause false regenerations. See Pitfall 2 in
02-RESEARCH.md.

All heavy imports (whisper, jiwer, whisper_normalizer) are deferred inside functions
so this module loads cleanly on Windows without GPU or model files.
"""
import os

# Configurable threshold. Indian-accented voice profiles may need 0.10.
# See Pitfall 6 in 02-RESEARCH.md: standard Whisper has +5-10% WER on Indian speech.
WER_THRESHOLD: float = float(os.environ.get("WER_THRESHOLD", "0.08"))

# ponytail: lazy caches — heavy imports deferred to first call
_whisper_cache: dict = {}
_normalizer = None  # EnglishTextNormalizer instance, lazily initialized inside compute_wer


def _get_whisper_model(model_size: str = "base"):
    """Return cached Whisper model, loading on first call."""
    if model_size not in _whisper_cache:
        import whisper  # ponytail: guarded — not available on Windows without GPU
        _whisper_cache[model_size] = whisper.load_model(model_size)
    return _whisper_cache[model_size]


def compute_wer(
    reference_spoken: str,
    audio_path: str,
    model_size: str = "base",
) -> float:
    """
    Transcribe audio_path with Whisper, normalize both sides, return WER.

    Uses model_size="base" by default for speed. For Indian-accented voice,
    consider model_size="large-v2" to reduce accent penalty on the verification
    pass. See Pitfall 6 in 02-RESEARCH.md.
    """
    global _normalizer
    from jiwer import wer  # ponytail: guarded import

    model = _get_whisper_model(model_size)
    result = model.transcribe(audio_path)
    hypothesis = result["text"]

    # Lazy init of EnglishTextNormalizer (guarded — not pre-installed on Windows)
    if _normalizer is None:
        from whisper_normalizer.english import EnglishTextNormalizer  # ponytail: guarded import
        _normalizer = EnglishTextNormalizer()

    ref_norm = _normalizer(reference_spoken)  # normalize reference — Pitfall 2
    hyp_norm = _normalizer(hypothesis)         # normalize hypothesis — Pitfall 2

    score = float(wer(ref_norm, hyp_norm))
    # ponytail: replace with logging.info if structured logs needed
    print(f"[verifier] WER={score:.4f}  ref_len={len(ref_norm.split())}  hyp_len={len(hyp_norm.split())}")
    return score


def check_wer(
    reference_spoken: str,
    audio_path: str,
    model_size: str = "base",
    threshold: float | None = None,
) -> tuple[str, float]:
    """
    Compute WER and return a (decision, score) tuple.

    decision values:
      "ok"         — WER ≤ threshold; alignment result is trustworthy
      "regenerate" — WER > threshold; retry TTS generation (one attempt)

    ponytail: the pipeline (align_pipeline.py) handles regenerate → retry →
    fallback escalation. verifier.py only ever returns "ok" or "regenerate";
    "fallback" is escalated by the caller after a second WER failure.
    """
    t = threshold if threshold is not None else WER_THRESHOLD
    score = compute_wer(reference_spoken, audio_path, model_size=model_size)

    if score <= t:
        return "ok", score
    return "regenerate", score
