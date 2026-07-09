"""
align/fallback.py — whisper-timestamped fallback path (ALIGN-04).

Triggered when:
  - align_known_transcript() returns NaN ratio > FALLBACK_NAN_THRESHOLD (20%)
  - check_wer() returns "regenerate" and a retry still exceeds threshold

Contract:
  fallback_align(wav_path) → list[dict]
  Each dict: {"w": str, "start": float, "end": float, "speaker": int}

CRITICAL (Pitfall 4 in 02-RESEARCH.md):
  whisper-timestamped uses {"text": ..., "start": ..., "end": ...} per word.
  The PRIMARY path uses {"w": ..., "start": ..., "end": ..., "speaker": 1}.
  This adapter normalizes the output. schema.py ONLY accepts the normalized shape.

whisper_timestamped is imported lazily — module loads cleanly on Windows.
"""
import math

# Matches FALLBACK_NAN_THRESHOLD in 02-RESEARCH.md Code Examples
FALLBACK_NAN_THRESHOLD: float = 0.20


def fallback_align(
    wav_path: str,
    model_size: str = "base",
    device: str = "cpu",
) -> list[dict]:
    """
    Produce word-level timestamps via whisper-timestamped DTW.

    Returns words[] in identical schema shape to aligner.py output.
    device defaults to "cpu" — whisper-timestamped is the fallback for when
    wav2vec2 GPU path fails; CPU is more reliable in that scenario.
    """
    import whisper_timestamped as wts  # ponytail: guarded — not available on Windows without GPU

    audio = wts.load_audio(wav_path)
    model = wts.load_model(model_size, device=device)

    result = wts.transcribe(
        model,
        audio,
        language="en",
        vad="silero",            # VAD improves word boundary precision
        detect_disfluencies=True,
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            start = w.get("start")
            end   = w.get("end")
            # Adapter: "text" key → "w" key; add "speaker" default
            # Normalize None timestamps to NaN (consistent with aligner.py)
            start = float(start) if start is not None else float("nan")
            end   = float(end)   if end   is not None else float("nan")
            words.append({
                "w":       w.get("text", "").strip(),  # adapter: "text" → "w" (Pitfall 4)
                "start":   round(start, 3),
                "end":     round(end,   3),
                "speaker": 1,   # no speaker info in single-speaker fallback
            })

    return words


def nan_ratio(words: list[dict]) -> float:
    """
    Fraction of words with NaN start timestamp.
    Use to decide whether to trigger fallback before WER check (structural failure).

    ponytail: simple count; add end-NaN check if stricter guard needed
    """
    if not words:
        return 1.0
    nan_count = sum(
        1 for w in words
        if w.get("start") is None or (
            isinstance(w.get("start"), float) and math.isnan(w["start"])
        )
    )
    return nan_count / len(words)
