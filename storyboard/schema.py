"""storyboard/schema.py — Pydantic models for LLM scene output and final timeline scenes.

Two-model design (see 03-RESEARCH.md Pattern 1):
  LLMSceneItem      — what the LLM returns. Contains NO timing fields.
  LLMScenesResponse — wrapper the LLM must return ({"scenes": [...]}).
  TimelineScene      — full scene written to timeline.json scenes[].
                       Timing injected from sentences[] AFTER the LLM call.

Invariant: LLM never sets start/end/duration. extra='ignore' drops them silently.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LLMSceneItem(BaseModel):
    """What the LLM returns per sentence. Contains NO timing fields.

    If the LLM hallucinates start/end/duration, Pydantic drops them silently
    via extra='ignore'. New fields default so old outputs still validate.
    A malformed rich scene (chart with 1 value, empty formula, 1-step process)
    downgrades to 'bullet' instead of failing validation.
    """
    model_config = ConfigDict(extra="ignore")

    on_screen_text: str
    visual_type: Literal[
        "bullet", "image", "code", "big-number", "comparison",
        "chart", "steps", "formula", "diagram",
    ]
    visual_query: str
    title: str = ""              # short 2-5 word heading for the scene
    bullets: list[str] = []      # key points (bullet) or stage names (steps)
    emoji: str = ""              # single emoji illustrating the concept
    chart_labels: list[str] = []  # chart only: 2-6 short labels
    chart_values: list[float] = []  # chart only: numbers matching labels
    formula: str = ""            # formula only: LaTeX without $ delimiters

    @field_validator("chart_values", mode="before")
    @classmethod
    def _coerce_numbers(cls, v):
        """LLMs return '45%', '1,000' — strip and coerce; drop non-numerics."""
        out = []
        for x in (v or []):
            if isinstance(x, str):
                x = x.replace("%", "").replace(",", "").strip()
            try:
                out.append(float(x))
            except (TypeError, ValueError):
                continue
        return out

    @model_validator(mode="after")
    def _downgrade_malformed(self):
        """Rich scene types degrade to 'bullet' when their data is unusable."""
        if self.visual_type == "chart":
            n = min(len(self.chart_labels), len(self.chart_values), 6)
            if n < 2:
                self.visual_type = "bullet"
            else:
                self.chart_labels = self.chart_labels[:n]
                self.chart_values = self.chart_values[:n]
        if self.visual_type == "steps" and len(self.bullets) < 2:
            self.visual_type = "bullet"
        if self.visual_type == "formula" and not self.formula.strip():
            self.visual_type = "bullet"
        return self


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
    visual: dict               # {"type", "query", + "image"/"credit" after diagram fetch}
    title: str = ""
    bullets: list[str] = []
    emoji: str = ""
    chart: dict = {}           # {"labels": [...], "values": [...]} for chart scenes
    formula: str = ""          # LaTeX for formula scenes
