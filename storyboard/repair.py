"""storyboard/repair.py — Parse, repair, and validate LLM JSON output.

Three-layer defense (see 03-RESEARCH.md Pattern 2):
  1. Strict json.loads + Pydantic model_validate
  2. json-repair + Pydantic model_validate
  3. Deterministic bullet fallback (never fails)

This function NEVER raises — it always returns a valid list[LLMSceneItem].
"""
import json
import logging

from pydantic import ValidationError

from storyboard.schema import LLMSceneItem, LLMScenesResponse


logger = logging.getLogger(__name__)


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

    # Layer 1: strict parse
    try:
        data = json.loads(content)
        items = LLMScenesResponse.model_validate(data).scenes
        if items:
            return _fit(items)
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        logger.warning("Strict parse failed: %s — trying repair", e)

    # Layer 2: json-repair then validate
    try:
        from json_repair import repair_json

        repaired = repair_json(content)
        # repair_json may return a string or a parsed object
        if isinstance(repaired, str):
            data = json.loads(repaired)
        else:
            data = repaired
        items = LLMScenesResponse.model_validate(data).scenes
        if items:
            logger.info("Repair succeeded — %d scenes recovered", len(items))
            return _fit(items)
    except Exception as e:
        logger.warning("Repair also failed: %s — falling back to bullets", e)

    # Layer 3: deterministic fallback — never crashes
    logger.info("Using deterministic bullet fallback for %d sentences", n_sentences)
    return _bullet_fallback(sentences)
