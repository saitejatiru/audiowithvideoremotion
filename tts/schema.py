"""Canonical timeline.json schema contract — Phase 1 defines this.

Every downstream phase imports from this module. DO NOT duplicate this schema elsewhere.

Invariants (all phases must respect):
  - durationSec always comes from the actual audio file (soundfile.info), never
    from the last word's end timestamp — trailing silence is real
  - wordRange is half-open: words[wordRange[0]:wordRange[1]]
  - words[].w contains the spoken (normalized) form; raw form is in word_map.json
    (written by normalize() via write_word_map())
  - scenes[].start/end are ALWAYS derived from sentence timestamps, never set by an LLM
"""
import json
from typing import Optional

import soundfile as sf
from pydantic import BaseModel


class TimelineAudio(BaseModel):
    path: str
    sampleRate: int = 24000
    durationSec: float


class TimelineWord(BaseModel):
    w: str
    start: float
    end: float
    speaker: int = 1
    confidence: Optional[float] = None


class TimelineSentence(BaseModel):
    idx: int
    text: str
    start: float
    end: float
    speaker: int = 1
    wordRange: list[int]  # half-open [first, last+1]


class TimelineMeta(BaseModel):
    lang: str = "en"
    wer: Optional[float] = None
    generator: str
    alignMethod: Optional[str] = None
    alignedAt: Optional[str] = None


class Timeline(BaseModel):
    audio: TimelineAudio
    words: list[TimelineWord] = []
    sentences: list[TimelineSentence] = []
    scenes: list[dict] = []  # populated by Phase 3
    meta: TimelineMeta


def write_phase1_timeline(
    audio_path: str,
    generator: str,
    output_path: str,
) -> None:
    """Write Phase 1 timeline.json: audio block populated, words/sentences/scenes empty.

    durationSec is derived from soundfile.info(audio_path).duration — never from word
    timestamps (invariant: trailing silence is real and must be preserved in durationSec).
    Phase 2 fills words[], sentences[], meta.wer, meta.alignMethod, meta.alignedAt.
    """
    duration = sf.info(audio_path).duration  # real file duration, not last word's end
    timeline = Timeline(
        audio=TimelineAudio(path=audio_path, durationSec=duration),
        meta=TimelineMeta(generator=generator),
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(timeline.model_dump_json(indent=2))


def write_word_map(word_map: list[dict], output_path: str) -> None:
    """Write normalizer word_map as JSON for Phase 4 caption rendering.

    Phase 4 (Remotion) reads word_map.json to display raw tokens (e.g. "$42.50")
    while aligning to spoken timestamps from timeline.json words[].
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(word_map, f, indent=2)
