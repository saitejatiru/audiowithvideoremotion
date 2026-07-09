"""Tests for post_process/post_processor.py.

Mocks subprocess.run to verify ffmpeg invocation and verification checks.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from post_process.post_processor import post_process_video, verify_metadata_stripped, PostProcessError


class TestPostProcessVideo:
    """post_process_video: calls ffmpeg subprocess to strip metadata and optimize."""

    def test_constructs_correct_ffmpeg_command(self, tmp_path):
        """Verify ffmpeg arguments are passed correctly."""
        inp = str(tmp_path / "in.mp4")
        out = str(tmp_path / "out.mp4")

        # Create dummy input file
        with open(inp, "w") as f:
            f.write("dummy")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("post_process.post_processor.subprocess.run", return_value=mock_result) as mock_run, \
             patch("post_process.post_processor.os.path.exists", return_value=True):
            post_process_video(inp, out)

        mock_run.assert_called()
        # Find the ffmpeg run call (there might be an ffprobe call after)
        ffmpeg_call = None
        for call in mock_run.call_args_list:
            args = call[0][0]
            if args[0] == "ffmpeg":
                ffmpeg_call = args
                break

        assert ffmpeg_call is not None
        assert "-map_metadata" in ffmpeg_call
        assert "-1" in ffmpeg_call
        assert "-movflags" in ffmpeg_call
        assert "+faststart" in ffmpeg_call
        assert "-fflags" in ffmpeg_call
        assert "+bitexact" in ffmpeg_call

    def test_raises_on_missing_input_file(self):
        """FileNotFoundError raised if input file is missing."""
        with pytest.raises(FileNotFoundError, match="Input video not found"):
            post_process_video("/nonexistent/in.mp4", "out.mp4")

    def test_raises_on_ffmpeg_failure(self, tmp_path):
        """PostProcessError raised if ffmpeg exits non-zero."""
        inp = str(tmp_path / "in.mp4")
        out = str(tmp_path / "out.mp4")
        with open(inp, "w") as f:
            f.write("dummy")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Unknown option: -movflags"

        with patch("post_process.post_processor.subprocess.run", return_value=mock_result):
            with pytest.raises(PostProcessError, match="ffmpeg failed"):
                post_process_video(inp, out)

    def test_raises_on_ffmpeg_timeout(self, tmp_path):
        """PostProcessError raised if ffmpeg times out."""
        import subprocess as sp
        inp = str(tmp_path / "in.mp4")
        out = str(tmp_path / "out.mp4")
        with open(inp, "w") as f:
            f.write("dummy")

        with patch("post_process.post_processor.subprocess.run", side_effect=sp.TimeoutExpired("cmd", 60)):
            with pytest.raises(PostProcessError, match="timed out"):
                post_process_video(inp, out)


class TestVerifyMetadataStripped:
    """verify_metadata_stripped: checks tags via ffprobe."""

    def test_succeeds_when_no_tags(self):
        """No exception raised if ffprobe shows empty tags."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"format": {}})

        with patch("post_process.post_processor.subprocess.run", return_value=mock_result):
            # Should not raise
            verify_metadata_stripped("test.mp4")

    def test_succeeds_with_benign_tags(self):
        """No exception raised if tags only contain benign format tags."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {"format": {"tags": {"major_brand": "mp42", "compatible_brands": "isom"}}}
        )

        with patch("post_process.post_processor.subprocess.run", return_value=mock_result):
            # Should not raise
            verify_metadata_stripped("test.mp4")

    def test_logs_warning_with_privacy_tags(self):
        """Logs a warning but does not raise on custom privacy tags."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {"format": {"tags": {"title": "My Secret Explainer", "comment": "Created by Antigravity"}}}
        )

        with patch("post_process.post_processor.subprocess.run", return_value=mock_result), \
             patch("post_process.post_processor.logger.warning") as mock_warn:
            verify_metadata_stripped("test.mp4")
            mock_warn.assert_called_once()
            assert "Retained tags" in mock_warn.call_args[0][0]
