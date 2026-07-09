"""
align/schema.py — timeline.json builder (ALIGN-03).

Contract:
  Input : words       — list of {"w", "start", "end", "speaker"[, "confidence"]}
          spoken_text — full normalized spoken script (for sentence splitting)
          wav_path    — path to source WAV (durationSec always from librosa)
          align_method — "whisperx-forced" | "whisper-timestamped-fallback"
          wer_score   — float 0–1 (from verifier, or 0.0 if not yet computed)
  Output: dict matching timeline.json schema (can be written with json.dumps)

Reuses tts.schema models — no forked duplicate (ALIGN-03 / I-02).
"""
import re
import json
from datetime import datetime, timezone

import librosa
import soundfile as sf

from tts.schema import Timeline, TimelineAudio, TimelineWord, TimelineSentence, TimelineMeta


def split_sentences(spoken_text: str) -> list[str]:
    """Split on sentence-ending punctuation. No external deps."""
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', spoken_text) if s.strip()]


def map_words_to_sentences(words: list[dict], sentences: list[str]) -> list[dict]:
    """
    Build sentences[] with start/end/wordRange populated from words[].

    wordRange is half-open: [first, last+1) — matches the schema in 02-RESEARCH.md.
    Handles token-count mismatch gracefully (TTS may skip/add words).
    """
    result = []
    w_idx = 0
    n_words = len(words)

    for s_idx, sent in enumerate(sentences):
        tokens = sent.split()
        first = w_idx
        last  = min(w_idx + len(tokens) - 1, n_words - 1)
        # Guard: never go past end of words list
        if first >= n_words:
            first = n_words - 1
            last  = n_words - 1

        result.append({
            "idx":       s_idx,
            "text":      sent,
            "start":     words[first]["start"],
            "end":       words[last]["end"],
            "speaker":   words[first].get("speaker", 1),
            "wordRange": [first, last + 1],  # half-open
        })
        w_idx = last + 1

    return result


def build_timeline(
    words: list[dict],
    spoken_text: str,
    wav_path: str,
    align_method: str,
    wer_score: float,
    lang: str = "en",
    generator: str = "vibevoice",
) -> dict:
    """
    Assemble the canonical timeline.json dict, validated via tts.schema models.

    durationSec ALWAYS comes from librosa.get_duration(path=) — never from words[-1]["end"].
    See Pitfall 5 in 02-RESEARCH.md.
    """
    # CRITICAL: duration from file, not from transcript (Pitfall 5)
    duration_sec = librosa.get_duration(path=wav_path)
    sample_rate  = sf.info(wav_path).samplerate  # fast header read, no full decode

    sents_text = split_sentences(spoken_text)
    sents_list = map_words_to_sentences(words, sents_text)

    timeline = Timeline(
        audio=TimelineAudio(
            path=wav_path,
            sampleRate=sample_rate,
            durationSec=round(duration_sec, 4),
        ),
        words=[TimelineWord(**w) for w in words],
        sentences=[TimelineSentence(**s) for s in sents_list],
        scenes=[],
        meta=TimelineMeta(
            lang=lang,
            wer=round(wer_score, 4),
            generator=generator,
            alignMethod=align_method,
            alignedAt=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return timeline.model_dump()


def write_timeline(timeline: dict, output_path: str) -> None:
    """Write timeline dict to JSON file with 2-space indent."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
