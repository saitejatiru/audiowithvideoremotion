"""storyboard/prompter.py — Build system and user prompts for the LLM storyboard call.

The system prompt embeds the LLMScenesResponse JSON schema so every OpenAI-compatible
provider (DeepSeek, MiniMax M3, Kimi K2.6) knows the exact output structure.
"""
import json

from storyboard.schema import LLMScenesResponse


def build_system_prompt(subject: str = "Auto-detect", grade: str = "Auto-detect") -> str:
    """Build the system prompt with the embedded JSON schema.

    Includes "json" in the prompt text — required by DeepSeek when using
    response_format={"type": "json_object"}.

    subject/grade: "Auto-detect" tells the LLM to infer both from the script;
    anything else is injected as the explicit audience.
    """
    schema = LLMScenesResponse.model_json_schema()

    if subject.startswith("Auto") and grade.startswith("Auto"):
        audience = (
            "First infer the SUBJECT and the student's GRADE level from the script, "
            "then match vocabulary, depth, and visual choices to that student."
        )
    else:
        subj = "" if subject.startswith("Auto") else f" studying {subject}"
        grd = "a school student" if grade.startswith("Auto") else f"a Class {grade} student"
        audience = (
            f"The audience is {grd}{subj} (CBSE/state boards). "
            "Match vocabulary, depth, and visual choices to that level."
        )

    return (
        "You are a storyboard designer for EDUCATIONAL explainer videos. "
        f"{audience} "
        "Your scenes must make the concept instantly understandable at a glance. "
        "Return ONLY valid JSON matching this schema exactly:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Rules:\n"
        "- One scene per sentence in the input.\n"
        "- visual_type options:\n"
        "  'bullet' — key points; 'image' — concept illustration (emoji); "
        "'code' — programming code; 'big-number' — a striking number/percentage; "
        "'comparison' — before/after or A vs B;\n"
        "  'chart' — when the sentence compares QUANTITIES: fill chart_labels "
        "(2-6 short labels) and chart_values (matching numbers);\n"
        "  'steps' — when the sentence describes a PROCESS or sequence: put 2-4 "
        "stage names (max 4 words each) in bullets, in order;\n"
        "  'formula' — for equations, laws, or math derivations: put valid LaTeX "
        "in the formula field, WITHOUT $ delimiters (e.g. E = mc^2, "
        "\\\\frac{dv}{dt} = a);\n"
        "  'diagram' — for physical structures or apparatus (heart, cell, circuit, "
        "ray optics, plant parts): visual_query must be a precise labeled-diagram "
        "search term, e.g. 'human heart labeled diagram'.\n"
        "  'animation' — for DYNAMIC Physics/Maths concepts that are best shown "
        "MOVING: forces/motion, waves, projectile paths, geometry, graphs being "
        "plotted, vectors. Put a clear step-by-step description in animation_brief "
        "(what appears, what moves, in what order). Use SPARINGLY — at most 1-2 per "
        "video, only where motion truly aids understanding.\n"
        "- title: a punchy 2-5 word heading, NOT a copy of the sentence.\n"
        "- bullets: short key points (max 6 words each); stage names for 'steps'.\n"
        "- emoji: exactly ONE emoji that captures the concept.\n"
        "- on_screen_text: one concise takeaway line (max 12 words), NOT the full sentence.\n"
        "- For 'big-number': put the number itself in on_screen_text, context in title.\n"
        "- For science/math scripts prefer 'diagram', 'formula', 'chart', and 'steps' "
        "over plain text scenes whenever the sentence allows it.\n"
        "- Vary visual_type across scenes — never use the same type 3 times in a row.\n"
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
