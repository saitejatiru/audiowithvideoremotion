"""Tests for storyboard/schema.py — Pydantic models for LLM output and timeline scenes."""
from pydantic import ValidationError
import pytest

from storyboard.schema import LLMSceneItem, LLMScenesResponse, TimelineScene


class TestLLMSceneItem:
    """LLMSceneItem: content-only model, extra fields silently dropped."""

    def test_valid_bullet(self):
        item = LLMSceneItem(
            on_screen_text="Hello world",
            visual_type="bullet",
            visual_query="hello",
        )
        assert item.on_screen_text == "Hello world"
        assert item.visual_type == "bullet"
        assert item.visual_query == "hello"

    def test_valid_image(self):
        item = LLMSceneItem(
            on_screen_text="A diagram of the system",
            visual_type="image",
            visual_query="system diagram",
        )
        assert item.visual_type == "image"

    def test_valid_code(self):
        item = LLMSceneItem(
            on_screen_text="print('hello')",
            visual_type="code",
            visual_query="python print",
        )
        assert item.visual_type == "code"

    def test_invalid_visual_type_raises(self):
        """visual_type must be exactly bullet/image/code — Pitfall 4."""
        with pytest.raises(ValidationError, match="visual_type"):
            LLMSceneItem(
                on_screen_text="test",
                visual_type="diagram",  # invalid
                visual_query="test",
            )

    def test_extra_fields_silently_dropped(self):
        """LLM hallucinating timing fields — extra='ignore' drops them (Pitfall 3)."""
        item = LLMSceneItem(
            on_screen_text="test",
            visual_type="bullet",
            visual_query="test",
            start=0.0,      # extra — should be silently dropped
            end=1.5,        # extra — should be silently dropped
            duration=1.5,   # extra — should be silently dropped
        )
        assert not hasattr(item, "start")
        assert not hasattr(item, "end")
        assert not hasattr(item, "duration")
        # Only declared fields survive
        dump = item.model_dump()
        assert set(dump.keys()) == {"on_screen_text", "visual_type", "visual_query"}

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            LLMSceneItem(on_screen_text="test", visual_type="bullet")
            # missing visual_query


class TestLLMScenesResponse:
    """LLMScenesResponse: wrapper for the list of scenes the LLM must return."""

    def test_valid_response(self):
        data = {
            "scenes": [
                {"on_screen_text": "a", "visual_type": "bullet", "visual_query": "a"},
                {"on_screen_text": "b", "visual_type": "image", "visual_query": "b"},
            ]
        }
        resp = LLMScenesResponse.model_validate(data)
        assert len(resp.scenes) == 2
        assert resp.scenes[0].visual_type == "bullet"

    def test_empty_scenes_valid(self):
        resp = LLMScenesResponse.model_validate({"scenes": []})
        assert resp.scenes == []

    def test_missing_scenes_key_raises(self):
        with pytest.raises(ValidationError):
            LLMScenesResponse.model_validate({"items": []})

    def test_nested_extra_fields_dropped(self):
        """Extra fields inside each scene item should be silently dropped."""
        data = {
            "scenes": [
                {
                    "on_screen_text": "test",
                    "visual_type": "bullet",
                    "visual_query": "test",
                    "start": 0.0,
                    "end": 1.0,
                }
            ]
        }
        resp = LLMScenesResponse.model_validate(data)
        dump = resp.scenes[0].model_dump()
        assert "start" not in dump
        assert "end" not in dump


class TestTimelineScene:
    """TimelineScene: full scene with timing injected from sentences[]."""

    def test_valid_scene(self):
        scene = TimelineScene(
            idx=0,
            sentenceRange=[0, 1],
            start=0.0,
            end=1.2,
            onScreenText="Hello world",
            visual={"type": "bullet", "query": "hello"},
        )
        assert scene.idx == 0
        assert scene.sentenceRange == [0, 1]
        assert scene.start == 0.0
        assert scene.end == 1.2
        assert scene.visual["type"] == "bullet"

    def test_model_dump_for_json(self):
        """model_dump() output must be JSON-serializable for timeline.json."""
        scene = TimelineScene(
            idx=1,
            sentenceRange=[1, 2],
            start=1.2,
            end=3.5,
            onScreenText="Test sentence",
            visual={"type": "image", "query": "test"},
        )
        dump = scene.model_dump()
        assert isinstance(dump, dict)
        assert dump["idx"] == 1
        assert dump["sentenceRange"] == [1, 2]
