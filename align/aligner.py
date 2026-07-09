"""
align/aligner.py — Primary forced-alignment path (ALIGN-01).

Contract:
  Input : wav_path (str, 16kHz or any SR — resampled internally)
          spoken_text (str) — MUST be number/symbol-expanded (Phase 1 contract)
  Output: dict with key "words": list of {"w", "start", "end", "speaker", "confidence"?}

whisperx is imported lazily — module loads cleanly on Windows without GPU/whisperx installed.
"""
import re
import math
import numpy as np
import librosa

# ponytail: global model cache; per-language cache if multi-lang needed later
_align_model_cache: dict = {}


def _get_device() -> str:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_align_model(lang: str, device: str):
    key = (lang, device)
    if key not in _align_model_cache:
        import whisperx  # ponytail: guarded — not available on Windows dev machine
        _align_model_cache[key] = whisperx.load_align_model(
            language_code=lang, device=device
        )
    return _align_model_cache[key]


def align_known_transcript(
    wav_path: str,
    spoken_text: str,
    device: str | None = None,
    lang: str = "en",
) -> dict:
    """
    Forced-align a known spoken transcript to audio via WhisperX wav2vec2.

    Returns {"words": [{"w", "start", "end", "speaker", "confidence"?}]}

    Raises ValueError if spoken_text is empty.
    Requires GPU + whisperx; raises ImportError on Windows without it.
    """
    if not spoken_text.strip():
        raise ValueError("spoken_text must not be empty")

    import whisperx  # ponytail: guarded import — fails fast on Windows with clear error

    device = device or _get_device()

    # WhisperX expects 16kHz float32 mono
    audio, _ = librosa.load(wav_path, sr=16000, mono=True)
    audio = audio.astype(np.float32)
    duration = len(audio) / 16000.0

    model_a, metadata = _load_align_model(lang, device)

    # CRITICAL: split into sentence-level segments (avoid wav2vec2 attention span
    # degradation on audio > ~30s). See Pitfall 3 in 02-RESEARCH.md.
    sentences = _split_to_segments(spoken_text, duration)

    result = whisperx.align(
        sentences, model_a, metadata, audio, device=device,
        return_char_alignments=False,
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            start = w.get("start")
            end   = w.get("end")
            # Normalize None → NaN so callers can check math.isnan()
            start = float(start) if start is not None else float("nan")
            end   = float(end)   if end   is not None else float("nan")
            entry = {
                "w":       w.get("word", "").strip(),
                "start":   round(start, 3),
                "end":     round(end,   3),
                "speaker": 1,  # single-speaker default; Phase 2 open question defers multi-speaker
            }
            score = w.get("score")
            if score is not None:
                entry["confidence"] = round(float(score), 4)
            words.append(entry)

    return {"words": words}


def _split_to_segments(spoken_text: str, total_duration: float) -> list[dict]:
    """
    Split spoken_text into sentence-level segments with estimated start/end times.
    The aligner will refine the times; these are starting bounds only.
    """
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', spoken_text) if s.strip()]
    if not raw_sentences:
        raw_sentences = [spoken_text.strip()]

    n = len(raw_sentences)
    # Uniform time estimates — aligner refines these
    segment_duration = total_duration / n
    return [
        {
            "text":  text,
            "start": round(i * segment_duration, 3),
            "end":   round((i + 1) * segment_duration, 3),
        }
        for i, text in enumerate(raw_sentences)
    ]
