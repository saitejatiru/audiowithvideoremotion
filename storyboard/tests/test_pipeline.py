"""Tests for storyboard/pipeline.py — full pipeline with mocked LLM client.

All tests monkeypatch call_llm to avoid real API calls.
Tests verify:
  - inject_timing produces correct scene boundaries from sentences
  - storyboard_pipeline mutates timeline["scenes"] correctly
  - Pipeline handles LLM failure gracefully (fallback)
  - Output file is written when output_path is set
"""
import json
from unittest.mock import patch

import pytest

from storyboard.schema import LLMSceneItem, LLMScenesResponse, TimelineScene
from storyboard.pipeline import inject_timing, storyboard_pipeline


class TestInjectTiming:
    """inject_timing: scene boundaries clamped to sentence boundaries (STORY-03)."""

    def test_correct_count(self, sample_sentences):
        items = [
            LLMSceneItem(on_screen_text=s["text"], visual_type="bullet", visual_query="q")
            for s in sample_sentences
        ]
        scenes = inject_timing(items, sample_sentences)
        assert len(scenes) == len(sample_sentences)

    def test_timing_from_sentences(self, sample_sentences):
        """Scene start/end must match sentence start/end exactly."""
        items = [
            LLMSceneItem(on_screen_text="text", visual_type="image", visual_query="q")
            for _ in sample_sentences
        ]
        scenes = inject_timing(items, sample_sentences)
        for scene, sent in zip(scenes, sample_sentences):
            assert scene["start"] == sent["start"]
            assert scene["end"] == sent["end"]

    def test_sentence_range_half_open(self, sample_sentences):
        """sentenceRange must be half-open [idx, idx+1]."""
        items = [
            LLMSceneItem(on_screen_text="t", visual_type="code", visual_query="q")
            for _ in sample_sentences
        ]
        scenes = inject_timing(items, sample_sentences)
        for i, scene in enumerate(scenes):
            assert scene["sentenceRange"] == [i, i + 1]

    def test_visual_field_structure(self, sample_sentences):
        items = [
            LLMSceneItem(on_screen_text="t", visual_type="image", visual_query="sunset")
            for _ in sample_sentences
        ]
        scenes = inject_timing(items, sample_sentences)
        for scene in scenes:
            assert scene["visual"]["type"] == "image"
            assert scene["visual"]["query"] == "sunset"

    def test_idx_sequential(self, sample_sentences):
        items = [
            LLMSceneItem(on_screen_text="t", visual_type="bullet", visual_query="q")
            for _ in sample_sentences
        ]
        scenes = inject_timing(items, sample_sentences)
        for i, scene in enumerate(scenes):
            assert scene["idx"] == i


class TestStoryboardPipeline:
    """Full pipeline with mocked LLM client."""

    def _mock_llm_response(self, sentences):
        """Create a valid JSON response string matching the expected schema."""
        data = LLMScenesResponse(
            scenes=[
                LLMSceneItem(
                    on_screen_text=s["text"],
                    visual_type="bullet",
                    visual_query=" ".join(s["text"].split()[:2]),
                )
                for s in sentences
            ]
        )
        return data.model_dump_json()

    def test_pipeline_populates_scenes(self, sample_timeline, sample_sentences):
        """Pipeline must populate timeline['scenes'] with correct count."""
        mock_response = self._mock_llm_response(sample_sentences)

        with patch("storyboard.pipeline.call_llm", return_value=mock_response):
            result = storyboard_pipeline(sample_timeline)

        assert len(result["scenes"]) == len(sample_sentences)

    def test_pipeline_scene_boundaries_match_sentences(self, sample_timeline, sample_sentences):
        """Every scene boundary must match its sentence boundary."""
        mock_response = self._mock_llm_response(sample_sentences)

        with patch("storyboard.pipeline.call_llm", return_value=mock_response):
            result = storyboard_pipeline(sample_timeline)

        for scene, sent in zip(result["scenes"], sample_sentences):
            assert scene["start"] == sent["start"]
            assert scene["end"] == sent["end"]

    def test_pipeline_fallback_on_llm_failure(self, sample_timeline, sample_sentences):
        """When LLM call raises, pipeline falls back to bullets without crashing."""
        with patch("storyboard.pipeline.call_llm", side_effect=Exception("API error")):
            result = storyboard_pipeline(sample_timeline)

        assert len(result["scenes"]) == len(sample_sentences)
        # Fallback produces bullets
        for scene in result["scenes"]:
            assert scene["visual"]["type"] == "bullet"

    def test_pipeline_fallback_on_empty_content(self, sample_timeline, sample_sentences):
        """When LLM returns empty string, pipeline falls back."""
        with patch("storyboard.pipeline.call_llm", return_value=""):
            result = storyboard_pipeline(sample_timeline)

        assert len(result["scenes"]) == len(sample_sentences)

    def test_pipeline_writes_output_file(self, sample_timeline, sample_sentences, tmp_path):
        """When output_path is set, pipeline writes updated timeline to disk."""
        mock_response = self._mock_llm_response(sample_sentences)
        out = str(tmp_path / "timeline.json")

        with patch("storyboard.pipeline.call_llm", return_value=mock_response):
            storyboard_pipeline(sample_timeline, output_path=out)

        assert (tmp_path / "timeline.json").exists()
        with open(out) as f:
            written = json.load(f)
        assert len(written["scenes"]) == len(sample_sentences)

    def test_pipeline_empty_sentences(self):
        """Timeline with no sentences should produce empty scenes[]."""
        timeline = {
            "audio": {"path": "t.wav", "sampleRate": 24000, "durationSec": 1.0},
            "words": [],
            "sentences": [],
            "scenes": [],
            "meta": {"lang": "en", "generator": "test"},
        }
        result = storyboard_pipeline(timeline)
        assert result["scenes"] == []

    def test_pipeline_returns_updated_dict(self, sample_timeline, sample_sentences):
        """Pipeline must return the same dict object, mutated in place."""
        mock_response = self._mock_llm_response(sample_sentences)

        with patch("storyboard.pipeline.call_llm", return_value=mock_response):
            result = storyboard_pipeline(sample_timeline)

        assert result is sample_timeline
        assert "scenes" in result
