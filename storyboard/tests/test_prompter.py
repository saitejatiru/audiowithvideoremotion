"""Tests for storyboard/prompter.py — system and user prompt generation."""
from storyboard.prompter import build_system_prompt, build_user_prompt


class TestBuildSystemPrompt:
    """System prompt must embed the JSON schema for all providers."""

    def test_contains_visual_type(self):
        prompt = build_system_prompt()
        assert "visual_type" in prompt

    def test_contains_on_screen_text(self):
        prompt = build_system_prompt()
        assert "on_screen_text" in prompt

    def test_contains_visual_query(self):
        prompt = build_system_prompt()
        assert "visual_query" in prompt

    def test_contains_json_keyword(self):
        """DeepSeek requires 'json' in the prompt when using json_object mode."""
        prompt = build_system_prompt()
        assert "json" in prompt.lower()

    def test_contains_schema_structure(self):
        """Prompt must contain the scenes array definition from model_json_schema."""
        prompt = build_system_prompt()
        assert "scenes" in prompt

    def test_prohibits_timing(self):
        """Prompt must tell LLM not to include timing."""
        prompt = build_system_prompt()
        assert "timing" in prompt.lower() or "duration" in prompt.lower()


class TestBuildUserPrompt:
    """User prompt must list sentences and request exact count."""

    def test_contains_sentence_texts(self, sample_sentences):
        prompt = build_user_prompt(sample_sentences)
        for s in sample_sentences:
            assert s["text"] in prompt

    def test_contains_sentence_count(self, sample_sentences):
        prompt = build_user_prompt(sample_sentences)
        assert str(len(sample_sentences)) in prompt

    def test_numbered_list(self, sample_sentences):
        prompt = build_user_prompt(sample_sentences)
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt

    def test_requests_exact_count(self, sample_sentences):
        prompt = build_user_prompt(sample_sentences)
        assert "exactly" in prompt.lower()
