# Phase 3: Storyboard - Research

**Researched:** 2026-07-09
**Domain:** LLM structured output / OpenAI-compatible APIs / Pydantic v2 schema validation
**Confidence:** HIGH

## Summary

Phase 3 adds a `storyboard/` Python module that reads `timeline.json` (sentences[], words[]),
calls an OpenAI-compatible LLM (MiniMax M3, DeepSeek, or Kimi K2.6) to generate per-sentence
scene content, validates the output against a Pydantic schema, repairs malformed JSON with
`json-repair`, and falls back deterministically to plain bullets when the LLM output cannot
be repaired. Timing is never touched by the LLM — all start/end values are injected from
`sentences[]` after the fact.

The LLM's only job is to produce three fields per sentence: `on_screen_text` (what to display),
`visual_type` ("bullet", "image", or "code"), and `visual_query` (keyword for b-roll). The
pipeline zips this array against `sentences[]` to produce `scenes[]` with full timing. The
`tts/schema.py` `Timeline` model's `scenes: list[dict]` field is already the insertion point —
Phase 3 populates it and writes back to `timeline.json`.

Structured JSON output with `json_object` mode is the universal choice across all three target
LLMs. DeepSeek's native API supports only `json_object` (not `json_schema`); MiniMax M3 and Kimi
K2.6 support both. Using `json_object` + Pydantic validation + `json-repair` covers all providers
without branching, and the deterministic fallback makes the path crash-proof.

**Primary recommendation:** `storyboard/` module with four files: schema.py → prompter.py → client.py → repair.py → pipeline.py. Use `response_format={"type": "json_object"}` for all providers; inject timing post-LLM; use `json-repair` + Pydantic for the repair path; deterministic bullet fallback as final safety net.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STORY-01 | LLM generates a per-sentence storyboard (visual, on-screen text, scene) from script + sentences | OpenAI-compatible client + `json_object` mode; system prompt embeds schema description; LLMScenesResponse model defines the output contract |
| STORY-02 | Storyboard output is schema-validated JSON with a repair/fallback path | `json-repair` 0.61.2 for parse repair; Pydantic v2 `model_validate()` for schema validation; deterministic bullet fallback when both fail |
| STORY-03 | Scene boundaries clamp to sentence boundaries (a scene can never straddle a word) | Timing injected from `sentences[]` after LLM call — LLM output contains zero timing fields; scene idx maps 1:1 to sentence idx |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=1.0.0 | OpenAI-compatible HTTP client | All three target LLMs expose OpenAI-compatible endpoints; single client, env-var base_url swap |
| pydantic | >=2.0 | Schema definition + response validation | Already used in tts/schema.py; `model_json_schema()` generates prompt-embeddable schema |
| json-repair | >=0.61.2 (latest PyPI as of 2026-07) | Repair malformed LLM JSON | Purpose-built for LLM JSON failures; handles truncation, missing braces, extra words |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest (already in align/requirements.txt) | Test runner | All tests |
| unittest.mock | stdlib | Monkeypatching LLM client | Pipeline tests; avoids real API calls in CI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json_object` mode | `json_schema` mode (MiniMax M3, Kimi K2.6) | `json_schema` gives hard schema guarantee but DeepSeek doesn't support it; `json_object` + Pydantic covers all providers uniformly |
| `json-repair` | Manual regex repair | `json-repair` handles 30+ LLM failure patterns; manual regex only handles the one pattern you test |
| Custom prompt retry | `instructor` library | `instructor` is another dep; repair + fallback is 20 lines and covers this use case entirely |

**Installation:**
```bash
pip install openai json-repair
# pydantic already in project
```

---

## Architecture Patterns

### Recommended Project Structure
```
storyboard/
├── __init__.py           # exports: storyboard_pipeline
├── schema.py             # LLMSceneItem, LLMScenesResponse, TimelineScene models
├── prompter.py           # build_system_prompt(), build_user_prompt(sentences)
├── client.py             # call_llm(messages, base_url, api_key, model) -> str
├── repair.py             # parse_and_validate(content) -> list[LLMSceneItem] | fallback
├── pipeline.py           # storyboard_pipeline(timeline: dict, ...) -> dict
└── tests/
    ├── __init__.py
    ├── conftest.py       # shared fixtures: sample_timeline, sample_sentences
    ├── test_schema.py    # LLMSceneItem validation, TimelineScene injection
    ├── test_prompter.py  # prompt contains schema, sentence texts
    ├── test_repair.py    # json.loads path, json_repair path, fallback path
    └── test_pipeline.py  # full pipeline (LLM client monkeypatched)
```

### Pattern 1: LLM Output vs. Timeline Scene (Two-Model Design)

**What:** The LLM only knows about content fields. Timing fields are injected after the fact.
**When to use:** Always — this enforces STORY-03 at the type level.

```python
# Source: tts/schema.py invariant + project plan arc
from typing import Literal
from pydantic import BaseModel

class LLMSceneItem(BaseModel):
    """What the LLM returns. Contains NO timing fields."""
    on_screen_text: str
    visual_type: Literal["bullet", "image", "code"]
    visual_query: str

class LLMScenesResponse(BaseModel):
    """Wrapper the LLM must return."""
    scenes: list[LLMSceneItem]

class TimelineScene(BaseModel):
    """Full scene written to timeline.json scenes[]. Never LLM-set fields: idx, sentenceRange, start, end."""
    idx: int
    sentenceRange: list[int]   # half-open [first, last+1] matching wordRange convention
    start: float
    end: float
    onScreenText: str
    visual: dict               # {"type": "bullet|image|code", "query": "..."}
```

### Pattern 2: Parse → Repair → Fallback

**What:** Three-layer defense against bad LLM output.
**When to use:** Always — mandatory per STORY-02.

```python
# Source: json-repair PyPI docs + Pydantic v2 model_validate
import json
from json_repair import repair_json
from pydantic import ValidationError

def parse_and_validate(content: str, n_sentences: int) -> list[LLMSceneItem]:
    """Returns validated LLMSceneItem list, or deterministic fallback. Never raises."""
    # Layer 1: strict parse
    try:
        data = json.loads(content)
        items = LLMScenesResponse.model_validate(data).scenes
        if len(items) == n_sentences:
            return items
    except (json.JSONDecodeError, ValidationError, Exception):
        pass

    # Layer 2: repair then validate
    try:
        data = json.loads(repair_json(content))
        items = LLMScenesResponse.model_validate(data).scenes
        if len(items) == n_sentences:
            return items
    except Exception:
        pass

    # Layer 3: deterministic fallback — never crashes
    return _bullet_fallback(sentences)
```

### Pattern 3: OpenAI-Compatible Client

**What:** Single client that works for all three LLMs via base_url env var.
**When to use:** All LLM calls.

```python
# Source: DeepSeek API docs, MiniMax M3 docs, Kimi K2.6 Moonshot docs
import os
from openai import OpenAI

def call_llm(messages: list[dict], *, base_url: str, api_key: str, model: str) -> str:
    """Returns raw content string. Caller handles parse."""
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},  # universal; all three support it
        max_tokens=2048,   # sufficient for ~30-sentence storyboard
        temperature=0.3,   # low for deterministic schema adherence
    )
    return response.choices[0].message.content or ""
```

### Pattern 4: Timing Injection (STORY-03 enforcement)

**What:** After LLM returns scenes, inject timing from sentences[].
**When to use:** Always, immediately after parse_and_validate.

```python
# Source: tts/schema.py wordRange convention
def inject_timing(items: list[LLMSceneItem], sentences: list[dict]) -> list[dict]:
    """1:1 zip — one scene per sentence. Timing from sentences[], never from LLM."""
    result = []
    for i, (item, sent) in enumerate(zip(items, sentences)):
        result.append(TimelineScene(
            idx=i,
            sentenceRange=[sent["idx"], sent["idx"] + 1],  # half-open, 1 sentence
            start=sent["start"],
            end=sent["end"],
            onScreenText=item.on_screen_text,
            visual={"type": item.visual_type, "query": item.visual_query},
        ).model_dump())
    return result
```

### Pattern 5: System Prompt with Embedded Schema

**What:** Embed the JSON schema description directly in the system prompt so all providers know the expected structure.
**Why needed:** DeepSeek requires "json" in the prompt; all providers benefit from explicit schema.

```python
import json

def build_system_prompt() -> str:
    schema = LLMScenesResponse.model_json_schema()
    return (
        "You are a storyboard designer for explainer videos. "
        "Return ONLY valid JSON matching this schema exactly:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Rules:\n"
        "- One scene per sentence in the input.\n"
        "- visual_type must be exactly: 'bullet', 'image', or 'code'.\n"
        "- visual_query is a short keyword for b-roll image search.\n"
        "- Do NOT include timing, durations, or frame numbers."
    )
```

### Anti-Patterns to Avoid

- **LLM sets `start`/`end`:** Violates STORY-03 and the core project principle. LLMSceneItem has no such fields; if the LLM returns them, Pydantic with `extra='ignore'` drops them silently.
- **Parsing `response.choices[0].message.content` without null check:** DeepSeek occasionally returns empty content. Always guard: `content or ""`.
- **Counting on scene count matching sentence count:** LLMs sometimes group sentences. Validate `len(items) == n_sentences`; if mismatch, trigger repair/fallback.
- **Using `stream=True` with `response_format`:** MiniMax M3 docs note stream and response_format are mutually exclusive. Never use streaming for storyboard calls.
- **Importing openai at module level unconditionally:** Follow project pattern — guard heavy imports inside function body so `storyboard/__init__.py` loads on Windows without API keys.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Malformed JSON repair | Custom regex or string manipulation | `json-repair` | Handles 30+ LLM failure patterns (truncation, missing braces, extra words, unescaped chars) |
| Schema generation for prompt | Manual JSON Schema dict | `model_json_schema()` | Stays in sync with Pydantic model automatically; no drift |
| HTTP retry + timeout | Custom retry loop | openai SDK's built-in retry | SDK handles 429, 5xx backoff; adding manual loop duplicates it |
| JSON Schema strict enforcement | Custom constrained-decoding plumbing | `json_object` + Pydantic validation | Good enough; adding `json_schema` mode adds provider branching for marginal gain |

**Key insight:** The repair + Pydantic validation layer is more robust than relying on constrained decoding alone (which still fails on truncation and empty content edge cases).

---

## Common Pitfalls

### Pitfall 1: Scene Count Mismatch
**What goes wrong:** LLM returns N-1 or N+1 scenes when given N sentences. Zip truncates silently.
**Why it happens:** LLMs sometimes merge short consecutive sentences or split long ones.
**How to avoid:** Validate `len(items) == n_sentences` as part of parse_and_validate; any mismatch triggers the repair/fallback path.
**Warning signs:** Silent scene count drop; last sentences have no scenes in output.

### Pitfall 2: Empty LLM Content
**What goes wrong:** `response.choices[0].message.content` is `None` or `""`.
**Why it happens:** DeepSeek documented this edge case; also occurs when `max_tokens` is too low.
**How to avoid:** Guard with `content or ""`; set `max_tokens >= 2048`; empty string triggers fallback path immediately.
**Warning signs:** `json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.

### Pitfall 3: LLM Injects Timing Fields
**What goes wrong:** LLM adds `start`, `end`, or `duration` fields to scene output.
**Why it happens:** Training data shows scenes with timing; LLM generalizes.
**How to avoid:** `LLMSceneItem` does not declare those fields; set `model_config = ConfigDict(extra='ignore')` so Pydantic drops extras silently.
**Warning signs:** Output scenes have timing that doesn't match alignment data.

### Pitfall 4: visual_type Hallucination
**What goes wrong:** LLM returns `"bullet_point"` or `"diagram"` instead of the three valid types.
**Why it happens:** LLMs paraphrase even with explicit instructions.
**How to avoid:** `Literal["bullet", "image", "code"]` on the Pydantic field; Pydantic raises `ValidationError` on invalid value; repair/fallback triggers.
**Warning signs:** `ValidationError: visual_type — Input should be 'bullet', 'image' or 'code'`.

### Pitfall 5: Deferred Import Pattern (Windows)
**What goes wrong:** `import openai` at module top level can fail on Windows in RED test state if env vars are not set or package not installed.
**Why it happens:** Project convention (see STATE.md) is to defer heavy imports inside function bodies.
**How to avoid:** Follow align/ pattern — `openai` import inside `call_llm()` body; storyboard module loads cleanly for import-only tests.
**Warning signs:** `ModuleNotFoundError` during `pytest --collect-only`.

---

## Code Examples

### Deterministic Fallback
```python
# Source: PROJECT_PLAN.md edge cases + project pattern
def _bullet_fallback(sentences: list[dict]) -> list[LLMSceneItem]:
    """Deterministic fallback: plain bullet per sentence. Never fails."""
    return [
        LLMSceneItem(
            on_screen_text=s["text"][:120],          # truncate for display
            visual_type="bullet",
            visual_query=" ".join(s["text"].split()[:3]),  # first 3 words as query
        )
        for s in sentences
    ]
```

### Pipeline Entry Point Signature
```python
# Source: align/align_pipeline.py pattern
def storyboard_pipeline(
    timeline: dict,
    *,
    base_url: str | None = None,    # defaults to env LLM_BASE_URL
    api_key: str | None = None,     # defaults to env LLM_API_KEY
    model: str | None = None,       # defaults to env LLM_MODEL
    output_path: str | None = None, # if set, writes back to timeline.json
) -> dict:
    """
    Reads timeline["sentences"], calls LLM, validates, injects timing,
    writes timeline["scenes"]. Returns updated timeline dict.

    Never raises on bad LLM output — falls back to deterministic bullets.
    """
```

### Environment Variables Convention
```python
# Follows project env-var pattern (API_SECRET in tts/server.py)
import os
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY  = os.environ.get("LLM_API_KEY", "")
LLM_MODEL    = os.environ.get("LLM_MODEL", "deepseek-chat")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manually parse LLM JSON with regex | `json-repair` library | 2023-2024 | Handles 30+ failure patterns; drop-in json.loads replacement |
| Prompt engineering alone for JSON | `response_format={"type":"json_object"}` | 2023 (GPT-4-turbo) | Hard JSON guarantee from API layer |
| Separate tool per LLM provider | OpenAI SDK + base_url swap | 2023-2024 | One client works for all OpenAI-compatible APIs |
| `json_object` only | `json_schema` mode (OpenAI, MiniMax M3, Kimi K2.6) | 2024-2025 | Schema enforced at decoding level; DeepSeek still lacks this |

**Provider-specific notes:**
- **DeepSeek** (as of 2026-07): native API only supports `json_object`; must include "json" in prompt; occasional empty content responses
- **MiniMax M3** (launched 2026-06-01): supports `json_schema`; streaming + response_format are mutually exclusive
- **Kimi K2.6** (Moonshot): supports `json_schema` and tool calling; OpenAI-compatible via `https://api.moonshot.ai/v1`

---

## Open Questions

1. **Scene grouping: 1:1 vs. multi-sentence scenes**
   - What we know: Project plan shows `"sentenceRange": [0, 1]` — one sentence per scene
   - What's unclear: Should adjacent short sentences be merged into one scene?
   - Recommendation: Start 1:1 (simplest, satisfies STORY-03); multi-sentence grouping is a v2 enhancement

2. **LLM_BASE_URL default provider**
   - What we know: DeepSeek, Kimi, Minimax all supported; DeepSeek cheapest
   - What's unclear: Which is primary for v1?
   - Recommendation: Default to DeepSeek (lowest cost); document env var to switch

3. **Write back to timeline.json or produce separate storyboard.json**
   - What we know: `tts/schema.py` `Timeline.scenes` is the insertion point; `align/` writes back to timeline.json
   - What's unclear: Phase 4 (Remotion) reads one file — `timeline.json`
   - Recommendation: Mutate and re-write `timeline.json` in-place (same pattern as align/)

---

## Sources

### Primary (HIGH confidence)
- DeepSeek API docs — `https://api-docs.deepseek.com/guides/json_mode` — json_object only, "json" in prompt required, empty content edge case
- MiniMax M3 docs / OpenRouter — json_schema supported, streaming incompatible with response_format, M3 launched 2026-06-01
- Kimi K2.6 Moonshot docs — `https://platform.kimi.ai/docs/guide/kimi-k2-6-quickstart` — json_schema supported, OpenAI-compatible
- json-repair PyPI — `https://pypi.org/project/json-repair/` — version 0.61.2, purpose-built for LLM JSON failures
- Pydantic v2 docs — `https://docs.pydantic.dev/latest/concepts/json_schema/` — `model_json_schema()`, `model_validate()`

### Secondary (MEDIUM confidence)
- OpenAI structured outputs docs — `https://platform.openai.com/docs/guides/structured-outputs` — pattern for Pydantic → response_format
- DeepInfra docs — `json_schema` via third-party provider works for DeepSeek models

### Tertiary (LOW confidence)
- MiniMax M2.5 GitHub issue #4 — `response_format` not supported in M2.5 (M3 resolves this per OpenRouter data)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — openai SDK and json-repair verified via official docs; Pydantic v2 in existing codebase
- Architecture: HIGH — follows established align/ module pattern directly; LLM behavior verified via provider docs
- Pitfalls: HIGH (Pitfalls 1-3 from provider docs); MEDIUM (Pitfall 5 from codebase pattern observation)

**Research date:** 2026-07-09
**Valid until:** 2026-08-09 (LLM APIs evolve fast; re-verify DeepSeek json_schema support)
