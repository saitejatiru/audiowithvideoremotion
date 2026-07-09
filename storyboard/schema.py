"""storyboard/schema.py — Pydantic models for LLM scene output and final timeline scenes.

Two-model design (see 03-RESEARCH.md Pattern 1):
  LLMSceneItem      — what the LLM returns. Contains NO timing fields.
  LLMScenesResponse — wrapper the LLM must return ({"scenes": [...]}).
  TimelineScene      — full scene written to timeline.json scenes[].
                       Timing injected from sentences[] AFTER the LLM call.

Invariant: LLM never sets start/end/duration. extra='ignore' drops them silently.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMSceneItem(BaseModel):
    """What the LLM returns per sentence. Contains NO timing fields.

    If the LLM hallucinates start/end/duration, Pydantic drops them silently
    via extra='ignore'.
    """
    model_config = ConfigDict(extra="ignore")

    on_screen_text: str
    visual_type: Literal["bullet", "image", "code"]
    visual_query: str


class LLMScenesResponse(BaseModel):
    """Wrapper the LLM must return. Validated via model_validate()."""
    scenes: list[LLMSceneItem]


class TimelineScene(BaseModel):
    """Full scene written to timeline.json scenes[].

    Never LLM-set fields: idx, sentenceRange, start, end.
    These are injected from sentences[] after the LLM call.
    """
    idx: int
    sentenceRange: list[int]   # half-open [first, last+1]
    start: float
    end: float
    onScreenText: str
    visual: dict               # {"type": "bullet|image|code", "query": "..."}
