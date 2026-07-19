"""Tests for storyboard/repair.py — parse, repair, and fallback paths.

Key invariant: parse_and_validate() NEVER raises. All three paths
(strict, repair, fallback) must produce valid LLMSceneItem lists.
"""
import json

import pytest

from storyboard.schema import LLMSceneItem, LLMScenesResponse
from storyboard.repair import parse_and_validate, _bullet_fallback


class TestBulletFallback:
    """Deterministic fallback generates safe bullets from sentences."""

    def test_returns_correct_count(self, sample_sentences):
        items = _bullet_fallback(sample_sentences)
        assert len(items) == len(sample_sentences)

    def test_all_bullet_type(self, sample_sentences):
        items = _bullet_fallback(sample_sentences)
        for item in items:
            assert item.visual_type == "bullet"

    def test_text_truncated_at_120(self):
        long_sent = [{"text": "A" * 200, "idx": 0}]
        items = _bullet_fallback(long_sent)
        assert len(items[0].on_screen_text) == 120

    def test_visual_query_first_3_words(self, sample_sentences):
        items = _bullet_fallback(sample_sentences)
        # First sentence: "Hello world." → query "Hello world."
        first_3 = " ".join(sample_sentences[0]["text"].split()[:3])
        assert items[0].visual_query == first_3


class TestParseAndValidate:
    """Three-layer defense: strict → repair → fallback."""

    def test_layer1_clean_json(self, sample_sentences):
        """Clean valid JSON is parsed and validated on the first try."""
        data = LLMScenesResponse(
            scenes=[
                LLMSceneItem(
                    on_screen_text=s["text"],
                    visual_type="bullet",
                    visual_query="test",
                )
                for s in sample_sentences
            ]
        )
        content = data.model_dump_json()
        items = parse_and_validate(content, sample_sentences)
        assert len(items) == len(sample_sentences)
        assert all(isinstance(i, LLMSceneItem) for i in items)

    def test_layer1_extra_fields_dropped(self, sample_sentences):
        """Extra fields in clean JSON are silently dropped by Pydantic."""
        raw = {
            "scenes": [
                {
                    "on_screen_text": s["text"],
                    "visual_type": "bullet",
                    "visual_query": "test",
                    "start": 0.0,    # extra — dropped
                    "duration": 1.0, # extra — dropped
                }
                for s in sample_sentences
            ]
        }
        content = json.dumps(raw)
        items = parse_and_validate(content, sample_sentences)
        assert len(items) == len(sample_sentences)

    def test_layer2_malformed_json_repaired(self, sample_sentences):
        """Malformed JSON (missing closing brace) repaired by json-repair."""
        pytest.importorskip("json_repair")
        # Valid JSON with a trailing missing brace
        raw = {
            "scenes": [
                {
                    "on_screen_text": s["text"],
                    "visual_type": "bullet",
                    "visual_query": "test",
                }
                for s in sample_sentences
            ]
        }
        # Remove the last character (closing brace) to simulate truncation
        content = json.dumps(raw)[:-1]
        items = parse_and_validate(content, sample_sentences)
        assert len(items) == len(sample_sentences)

    def test_layer3_gibberish_fallback(self, sample_sentences):
        """Complete gibberish triggers the deterministic fallback."""
        items = parse_and_validate("this is not json at all!!!", sample_sentences)
        assert len(items) == len(sample_sentences)
        assert all(item.visual_type == "bullet" for item in items)

    def test_layer3_empty_string_fallback(self, sample_sentences):
        """Empty string (DeepSeek Pitfall 2) triggers fallback."""
        items = parse_and_validate("", sample_sentences)
        assert len(items) == len(sample_sentences)

    def test_layer3_count_mismatch_fallback(self, sample_sentences):
        """Correct JSON but wrong scene count triggers fallback."""
        raw = {
            "scenes": [
                {
                    "on_screen_text": "only one",
                    "visual_type": "bullet",
                    "visual_query": "one",
                }
            ]
        }
        content = json.dumps(raw)
        items = parse_and_validate(content, sample_sentences)
        # Should fall back because count doesn't match
        assert len(items) == len(sample_sentences)
        assert all(item.visual_type == "bullet" for item in items)

    def test_one_malformed_scene_kept_others(self, sample_sentences):
        """A single bad scene item (e.g. truncated tail) must NOT discard the
        whole response — good scenes survive, bad ones become bullets."""
        raw = {
            "scenes": [
                {"on_screen_text": "a", "visual_type": "bullet", "visual_query": "a"},
                ["on_screen_text"],  # malformed (a list, like the truncation bug)
                {"on_screen_text": "c", "visual_type": "image", "visual_query": "c"},
            ]
        }
        items = parse_and_validate(json.dumps(raw), sample_sentences)
        assert len(items) == len(sample_sentences)
        # the two valid rich scenes are preserved (image type survived)
        assert any(i.visual_type == "image" for i in items)

    def test_never_raises(self, sample_sentences):
        """parse_and_validate must NEVER raise, no matter the input."""
        hostile_inputs = [
            "",
            "null",
            "[]",
            "42",
            '{"scenes": "not a list"}',
            '{"scenes": [{"bad": "schema"}]}',
            "<html>not json</html>",
            None.__repr__(),
        ]
        for inp in hostile_inputs:
            items = parse_and_validate(inp, sample_sentences)
            assert len(items) == len(sample_sentences)
            assert all(isinstance(i, LLMSceneItem) for i in items)
