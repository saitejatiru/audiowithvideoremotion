"""storyboard/prompter.py — Build system and user prompts for the LLM storyboard call.

The system prompt embeds the LLMScenesResponse JSON schema so every OpenAI-compatible
provider (DeepSeek, MiniMax M3, Kimi K2.6) knows the exact output structure.
"""
import json

from storyboard.schema import LLMScenesResponse


def build_system_prompt() -> str:
    """Build the system prompt with the embedded JSON schema.

    Includes "json" in the prompt text — required by DeepSeek when using
    response_format={"type": "json_object"}.
    """
    schema = LLMScenesResponse.model_json_schema()
    return (
        "You are a storyboard designer for explainer videos. "
        "Return ONLY valid JSON matching this schema exactly:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Rules:\n"
        "- One scene per sentence in the input.\n"
        "- visual_type must be exactly: 'bullet', 'image', or 'code'.\n"
        "- visual_query is a short keyword for b-roll image search.\n"
        "- on_screen_text is the concise text to display on screen for this scene.\n"
        "- Do NOT include timing, durations, or frame numbers."
    )


def build_user_prompt(sentences: list[dict]) -> str:
    """Build the user prompt from timeline sentences.

    Each sentence is numbered for the LLM to produce exactly one scene per sentence.
    """
    lines = []
    for i, s in enumerate(sentences):
        lines.append(f"{i + 1}. {s['text']}")
    return (
        "Generate a storyboard for this script. "
        f"There are {len(sentences)} sentences — return exactly {len(sentences)} scenes.\n\n"
        + "\n".join(lines)
    )
