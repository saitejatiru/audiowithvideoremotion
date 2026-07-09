"""storyboard/client.py — OpenAI-compatible LLM client.

Uses a single OpenAI SDK client with base_url swap to support DeepSeek, MiniMax M3,
and Kimi K2.6 without provider branching.

openai import is deferred inside call_llm() body — follows project pattern so
storyboard/ imports cleanly on Windows without API keys or the openai package.
"""
import os


# Environment variable defaults (project convention — see tts/server.py API_SECRET pattern)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


def call_llm(
    messages: list[dict],
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Call an OpenAI-compatible LLM and return the raw content string.

    Caller is responsible for parsing/validating the returned JSON.
    Uses response_format={"type": "json_object"} — universal across all target providers.

    Args:
        messages: Chat messages (system + user).
        base_url: Override LLM_BASE_URL env var.
        api_key: Override LLM_API_KEY env var.
        model: Override LLM_MODEL env var.

    Returns:
        Raw content string from the LLM response. Empty string if content is None
        (DeepSeek edge case — see Pitfall 2 in 03-RESEARCH.md).
    """
    # Deferred import — project pattern (Pitfall 5)
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key or LLM_API_KEY,
        base_url=base_url or LLM_BASE_URL,
    )
    try:
        response = client.chat.completions.create(
            model=model or LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=2048,
            temperature=0.3,
        )
    except Exception:
        # Some providers (e.g. NVIDIA NIM models) reject response_format —
        # retry bare; the repair layer handles non-strict JSON output.
        response = client.chat.completions.create(
            model=model or LLM_MODEL,
            messages=messages,
            max_tokens=2048,
            temperature=0.3,
        )
    # Guard against None content (Pitfall 2)
    return response.choices[0].message.content or ""
