"""storyboard/repair.py — Parse, repair, and validate LLM JSON output.

Three-layer defense (see 03-RESEARCH.md Pattern 2):
  1. Strict json.loads + Pydantic model_validate
  2. json-repair + Pydantic model_validate
  3. Deterministic bullet fallback (never fails)

This function NEVER raises — it always returns a valid list[LLMSceneItem].
"""
import json
import logging
import re

from pydantic import ValidationError

from storyboard.schema import LLMSceneItem, LLMScenesResponse


logger = logging.getLogger(__name__)

_SEQ_RE = re.compile(r"\b(first|then|next|after that|finally|step\s*\d)\b", re.I)
_NUM_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?\b")
_EQ_RE = re.compile(r"[A-Za-z0-9)\]]\s*=\s*[A-Za-z0-9(\[]")


def smart_fallback(sentences: list[dict]) -> list[LLMSceneItem]:
    """No-LLM storyboard from cheap text heuristics — animated, never plain.

    Conservative on purpose: no diagram scenes (a wrong labeled diagram is a
    correctness liability in education content); formula only on a clear
    equation match (invalid LaTeX renders as plain text in the component).
    """
    items = []
    for s in sentences:
        text = s["text"]
        title = " ".join(text.split()[:4]).rstrip(".,;:")
        nums = _NUM_RE.findall(text)
        if _EQ_RE.search(text):
            items.append(LLMSceneItem(
                on_screen_text=text[:120], visual_type="formula",
                visual_query=title, title=title, formula=text.strip()[:80],
            ))
        elif _SEQ_RE.search(text):
            parts = [p.strip() for p in re.split(
                r",|;|\bthen\b|\bnext\b|\bfinally\b", text, flags=re.I) if p.strip()]
            bullets = [" ".join(p.split()[:4]).rstrip(".,;:") for p in parts[:4]]
            # schema validator downgrades to bullet if fewer than 2 stages
            items.append(LLMSceneItem(
                on_screen_text=text[:120], visual_type="steps",
                visual_query=title, title=title, bullets=bullets,
            ))
        elif nums:
            items.append(LLMSceneItem(
                on_screen_text=nums[0], visual_type="big-number",
                visual_query=title, title=title,
            ))
        else:
            items.append(LLMSceneItem(
                on_screen_text=text[:120], visual_type="bullet",
                visual_query=" ".join(text.split()[:3]), title=title,
            ))
    return items


def _bullet_fallback(sentences: list[dict]) -> list[LLMSceneItem]:
    """Deterministic fallback: plain bullet per sentence. Never fails.

    Truncates on_screen_text to 120 chars and uses first 3 words as visual_query.
    """
    return [
        LLMSceneItem(
            on_screen_text=s["text"][:120],
            visual_type="bullet",
            visual_query=" ".join(s["text"].split()[:3]),
        )
        for s in sentences
    ]


def parse_and_validate(
    content: str,
    sentences: list[dict],
) -> list[LLMSceneItem]:
    """Parse LLM output JSON and validate against schema. Never raises.

    Args:
        content: Raw JSON string from the LLM.
        sentences: The original sentences list (used for count validation and fallback).

    Returns:
        Validated list of LLMSceneItem. Falls back to bullets if all parse paths fail.
    """
    n_sentences = len(sentences)

    def _fit(items: list[LLMSceneItem]) -> list[LLMSceneItem]:
        """Salvage a wrong-count response: trim extras, pad the tail with
        bullets. Rich scenes are kept — a count mismatch used to throw away
        the ENTIRE response, which flattened whole videos."""
        if len(items) != n_sentences:
            logger.warning(
                "LLM returned %d scenes for %d sentences — trimming/padding",
                len(items), n_sentences,
            )
            items = items[:n_sentences]
            items = items + _bullet_fallback(sentences[len(items):])
        return items

    def _items_from(data) -> list[LLMSceneItem]:
        """Validate scenes one-by-one, keeping the good ones. A single malformed
        scene (e.g. a truncated tail item) must NOT discard the whole response."""
        raw = data.get("scenes") if isinstance(data, dict) else data
        if not isinstance(raw, list):
            return []
        good = []
        for item in raw:
            try:
                good.append(LLMSceneItem.model_validate(item))
            except Exception:
                continue  # drop the bad scene; _fit pads it back as a bullet
        return good

    # Layer 1: strict parse
    try:
        items = _items_from(json.loads(content))
        if items:
            return _fit(items)
    except Exception as e:
        logger.warning("Strict parse failed: %s — trying repair", e)

    # Layer 2: json-repair then per-item validate
    try:
        from json_repair import repair_json

        repaired = repair_json(content)
        data = json.loads(repaired) if isinstance(repaired, str) else repaired
        items = _items_from(data)
        if items:
            logger.info("Repair succeeded — %d valid scenes recovered", len(items))
            return _fit(items)
    except Exception as e:
        logger.warning("Repair also failed: %s — falling back to bullets", e)

    # Layer 3: deterministic fallback — never crashes
    logger.info("Using deterministic bullet fallback for %d sentences", n_sentences)
    return _bullet_fallback(sentences)
