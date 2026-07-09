"""
align/align_pipeline.py — Phase 2 entry point (ALIGN-01 through ALIGN-04).

Usage:
    from align.align_pipeline import run_alignment
    timeline = run_alignment(
        wav_path="out.wav",
        spoken_text="Hello world. This is the normalized spoken text.",
        output_path="timeline.json",
    )

Returns the timeline dict (also written to output_path).

Escalation policy:
  1. Run primary alignment (WhisperX)
  2. If NaN ratio > 0.20 → skip WER, go straight to fallback
  3. Run WER check on primary result
  4. If WER "ok" → write timeline.json with alignMethod="whisperx-forced"
  5. If WER "regenerate" → caller should re-run TTS and retry; pipeline raises
     AlignmentDriftError with the WER score so the orchestrator (Phase 6) can retry
  6. If caller retries and WER still fails → pass use_fallback=True to force whisper-timestamped
  7. Fallback → write timeline.json with alignMethod="whisper-timestamped-fallback"
"""
from align.aligner   import align_known_transcript
from align.verifier  import check_wer, WER_THRESHOLD
from align.fallback  import fallback_align, nan_ratio, FALLBACK_NAN_THRESHOLD
from align.schema    import build_timeline, write_timeline


class AlignmentDriftError(Exception):
    """Raised when WER exceeds threshold after primary alignment.
    Caller should regenerate audio and retry, or pass use_fallback=True."""
    def __init__(self, wer_score: float):
        super().__init__(
            f"WER {wer_score:.3f} exceeds threshold {WER_THRESHOLD:.3f}. "
            "Regenerate audio or set use_fallback=True."
        )
        self.wer_score = wer_score


def run_alignment(
    wav_path: str,
    spoken_text: str,
    output_path: str = "timeline.json",
    use_fallback: bool = False,
    wer_model_size: str = "base",
    generator: str = "vibevoice",
) -> dict:
    """
    Run the full alignment pipeline and write timeline.json.

    Args:
        wav_path:        Path to the narration WAV (any sample rate; resampled internally).
        spoken_text:     Normalized spoken script from Phase 1 (MUST have no digit strings).
        output_path:     Where to write timeline.json.
        use_fallback:    True to skip primary alignment and use whisper-timestamped directly.
        wer_model_size:  Whisper model size for WER verification pass ("base", "large-v2").
        generator:       TTS generator name for timeline.json meta field.

    Returns:
        timeline dict (same content as written to output_path).

    Raises:
        AlignmentDriftError: if primary alignment WER exceeds threshold.
                             Set use_fallback=True on retry to bypass this.
    """
    # --- Path A: forced fallback (caller escalated after regenerate failed) ---
    if use_fallback:
        return _run_fallback_path(wav_path, spoken_text, output_path, generator)

    # --- Path B: primary WhisperX forced-alignment ---
    primary_result = align_known_transcript(wav_path, spoken_text)
    words = primary_result["words"]

    # Check NaN ratio first — structural failure is immediate fallback trigger
    nan_frac = nan_ratio(words)
    if nan_frac > FALLBACK_NAN_THRESHOLD:
        print(
            f"[align_pipeline] NaN ratio {nan_frac:.1%} > {FALLBACK_NAN_THRESHOLD:.0%} — "
            "structural alignment failure, switching to whisper-timestamped fallback."
        )
        return _run_fallback_path(wav_path, spoken_text, output_path, generator)

    # WER guard — semantic drift check
    decision, wer_score = check_wer(
        spoken_text, wav_path, model_size=wer_model_size
    )
    print(f"[align_pipeline] WER={wer_score:.4f} decision={decision}")

    if decision == "ok":
        tl = build_timeline(
            words=words,
            spoken_text=spoken_text,
            wav_path=wav_path,
            align_method="whisperx-forced",
            wer_score=wer_score,
            generator=generator,
        )
        write_timeline(tl, output_path)
        return tl

    # decision == "regenerate": raise so caller can retry TTS before re-aligning
    # ponytail: Phase 6 orchestrator wraps this in a retry loop (one attempt)
    raise AlignmentDriftError(wer_score)


def _run_fallback_path(
    wav_path: str,
    spoken_text: str,
    output_path: str,
    generator: str,
) -> dict:
    """whisper-timestamped fallback path. Always succeeds (no WER gate on fallback)."""
    words = fallback_align(wav_path)
    # ponytail: no WER check on fallback output — we accept whatever timestamps DTW gives
    tl = build_timeline(
        words=words,
        spoken_text=spoken_text,
        wav_path=wav_path,
        align_method="whisper-timestamped-fallback",
        wer_score=0.0,   # WER not computed for fallback path
        generator=generator,
    )
    write_timeline(tl, output_path)
    return tl
