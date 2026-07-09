"""Tests for render/render_bridge.py — Python bridge to Remotion CLI.

All tests mock subprocess to avoid actual Remotion/Node.js execution.
Tests verify correct command construction, error handling, and duration validation.
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from render.render_bridge import render_video, _get_video_duration, RenderError


@pytest.fixture
def sample_timeline_file(tmp_path):
    """Write a minimal timeline.json and return its path."""
    timeline = {
        "audio": {"path": "audio.wav", "sampleRate": 24000, "durationSec": 6.0},
        "words": [{"w": "Hello", "start": 0.0, "end": 0.5, "speaker": 1}],
        "sentences": [{"idx": 0, "text": "Hello", "start": 0.0, "end": 0.5, "speaker": 1, "wordRange": [0, 1]}],
        "scenes": [{"idx": 0, "sentenceRange": [0, 1], "start": 0.0, "end": 0.5, "onScreenText": "Hello", "visual": {"type": "bullet", "query": "hello"}}],
        "meta": {"lang": "en", "generator": "test"},
    }
    path = tmp_path / "timeline.json"
    path.write_text(json.dumps(timeline), encoding="utf-8")
    return str(path)


class TestRenderVideo:
    """render_video: subprocess bridge to npx remotion render."""

    def test_constructs_correct_command(self, sample_timeline_file, tmp_path):
        """Verify the command passed to subprocess is correct."""
        output = str(tmp_path / "out.mp4")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("render.render_bridge.subprocess.run", return_value=mock_result) as mock_run, \
             patch("render.render_bridge.os.path.exists", side_effect=lambda p: True), \
             patch("render.render_bridge._get_video_duration", return_value=6.0):
            render_video(sample_timeline_file, output)

        # Verify subprocess was called
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "npx"
        assert cmd[1] == "remotion"
        assert cmd[2] == "render"
        assert cmd[3] == "ExplainerVideo"
        assert "--props" in cmd

    def test_raises_on_missing_timeline(self, tmp_path):
        """FileNotFoundError when timeline.json doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Timeline not found"):
            render_video("/nonexistent/timeline.json", str(tmp_path / "out.mp4"))

    def test_raises_on_render_failure(self, sample_timeline_file, tmp_path):
        """RenderError when Remotion exits non-zero."""
        output = str(tmp_path / "out.mp4")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: composition not found"

        with patch("render.render_bridge.subprocess.run", return_value=mock_result):
            with pytest.raises(RenderError, match="Remotion render failed"):
                render_video(sample_timeline_file, output)

    def test_raises_on_timeout(self, sample_timeline_file, tmp_path):
        """RenderError when subprocess times out."""
        import subprocess as sp
        output = str(tmp_path / "out.mp4")

        with patch("render.render_bridge.subprocess.run", side_effect=sp.TimeoutExpired("cmd", 600)):
            with pytest.raises(RenderError, match="timed out"):
                render_video(sample_timeline_file, output)

    def test_raises_on_missing_output(self, sample_timeline_file, tmp_path):
        """RenderError when render exits 0 but no file produced."""
        output = str(tmp_path / "out.mp4")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        # os.path.exists returns True for timeline, False for output
        def mock_exists(path):
            return path == os.path.abspath(sample_timeline_file)

        with patch("render.render_bridge.subprocess.run", return_value=mock_result), \
             patch("render.render_bridge.os.path.exists", side_effect=mock_exists):
            with pytest.raises(RenderError, match="output not found"):
                render_video(sample_timeline_file, output)

    def test_custom_composition_id(self, sample_timeline_file, tmp_path):
        """Custom composition_id is passed to the command."""
        output = str(tmp_path / "out.mp4")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("render.render_bridge.subprocess.run", return_value=mock_result) as mock_run, \
             patch("render.render_bridge.os.path.exists", return_value=True), \
             patch("render.render_bridge._get_video_duration", return_value=6.0):
            render_video(sample_timeline_file, output, composition_id="CustomComp")

        cmd = mock_run.call_args[0][0]
        assert "CustomComp" in cmd


class TestGetVideoDuration:
    """_get_video_duration: ffprobe wrapper."""

    def test_returns_duration_on_success(self, tmp_path):
        """Returns float duration when ffprobe succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"format": {"duration": "6.033"}})

        with patch("render.render_bridge.subprocess.run", return_value=mock_result):
            d = _get_video_duration(str(tmp_path / "test.mp4"))
            assert d == pytest.approx(6.033)

    def test_returns_none_when_ffprobe_missing(self):
        """Returns None when ffprobe is not installed."""
        with patch("render.render_bridge.subprocess.run", side_effect=FileNotFoundError):
            assert _get_video_duration("test.mp4") is None

    def test_returns_none_on_bad_json(self):
        """Returns None when ffprobe output is not valid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with patch("render.render_bridge.subprocess.run", return_value=mock_result):
            assert _get_video_duration("test.mp4") is None
