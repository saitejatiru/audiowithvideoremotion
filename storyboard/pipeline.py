"""storyboard/pipeline.py — End-to-end storyboard generation pipeline.

Reads timeline["sentences"], calls the LLM, validates/repairs output,
injects timing from sentences[], and writes scenes[] back to the timeline.

Never raises on bad LLM output — falls back to deterministic bullets.
"""
import json
import logging
import os

from storyboard.schema import LLMSceneItem, TimelineScene
from storyboard.prompter import build_system_prompt, build_user_prompt
from storyboard.repair import parse_and_validate, smart_fallback
from storyboard.client import call_llm


logger = logging.getLogger(__name__)


def inject_timing(
    items: list[LLMSceneItem],
    sentences: list[dict],
) -> list[dict]:
    """1:1 zip — one scene per sentence. Timing from sentences[], never from LLM.

    Enforces STORY-03: scene boundaries are clamped to sentence boundaries.

    Args:
        items: Validated LLMSceneItem list (same length as sentences).
        sentences: The sentences[] from timeline.json.

    Returns:
        List of TimelineScene dicts ready for timeline["scenes"].
    """
    result = []
    for i, (item, sent) in enumerate(zip(items, sentences)):
        scene = TimelineScene(
            idx=i,
            sentenceRange=[sent["idx"], sent["idx"] + 1],  # half-open
            start=sent["start"],
            end=sent["end"],
            onScreenText=item.on_screen_text,
            visual={"type": item.visual_type, "query": item.visual_query},
            title=item.title,
            bullets=item.bullets,
            emoji=item.emoji,
            chart={"labels": item.chart_labels, "values": item.chart_values},
            formula=item.formula,
            animation_brief=item.animation_brief,
        )
        result.append(scene.model_dump())
    return result


def storyboard_pipeline(
    timeline: dict,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    output_path: str | None = None,
    subject: str = "Auto-detect",
    grade: str = "Auto-detect",
    animate_first: bool = False,
) -> dict:
    """Run the full storyboard generation pipeline.

    Reads timeline["sentences"], calls LLM, validates, injects timing,
    writes timeline["scenes"]. Returns updated timeline dict.

    Never raises on bad LLM output — falls back to deterministic bullets.

    Args:
        timeline: The timeline dict (from timeline.json).
        base_url: Override LLM_BASE_URL env var.
        api_key: Override LLM_API_KEY env var.
        model: Override LLM_MODEL env var.
        output_path: If set, writes updated timeline to this path.

    Returns:
        Updated timeline dict with scenes[] populated.
    """
    sentences = timeline.get("sentences", [])
    if not sentences:
        logger.warning("No sentences in timeline — skipping storyboard")
        timeline["scenes"] = []
        return timeline

    # Build prompts
    system_prompt = build_system_prompt(subject=subject, grade=grade, animate_first=animate_first)
    user_prompt = build_user_prompt(sentences)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call LLM
    llm_error = ""
    try:
        content = call_llm(
            messages,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        logger.info("LLM returned %d chars", len(content))
    except Exception as e:
        logger.warning("LLM call failed: %s — using fallback", e)
        llm_error = str(e)
        content = ""

    # Parse, validate, repair (never raises)
    items = parse_and_validate(content, sentences)

    # Surface silent degradation: empty LLM content, or scenes with none of
    # the rich fields set, means the deterministic fallback produced them.
    used_fallback = content == "" or all(
        not i.title and not i.emoji and not i.bullets for i in items
    )
    meta = timeline.setdefault("meta", {})
    meta["storyboard"] = "fallback" if used_fallback else "llm"
    if used_fallback:
        meta["storyboardError"] = llm_error or "LLM returned unusable output"
        logger.warning(
            "Storyboard degraded — %s. Check LLM_API_KEY / LLM_MODEL / LLM_BASE_URL",
            meta["storyboardError"],
        )
        # heuristic scenes: numbers, steps, formulas — animated even without LLM
        items = smart_fallback(sentences)

    # Inject timing from sentences (STORY-03)
    scenes = inject_timing(items, sentences)
    timeline["scenes"] = scenes

    # Optionally write back to file
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2, ensure_ascii=False)
        logger.info("Updated timeline written to %s", output_path)

    return timeline
