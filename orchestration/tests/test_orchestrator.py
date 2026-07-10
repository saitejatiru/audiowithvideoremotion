"""Tests for orchestration/orchestrator.py.

Verifies the generator sequence and failure handling by mocking all external module dependencies.
"""
import json
from unittest.mock import patch

from orchestration.orchestrator import orchestrate_video
from align.align_pipeline import AlignmentDriftError


def _write_timeline(wav_path, spoken_text, output_path, **kwargs):
    """Stand-in for run_alignment: writes a minimal timeline.json."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"sentences": [], "meta": {}}, f)


class TestOrchestrateVideo:
    """Tests the orchestrate_video generator."""

    @patch("orchestration.orchestrator.post_process_video")
    @patch("orchestration.orchestrator.render_video")
    @patch("orchestration.orchestrator.storyboard_pipeline")
    @patch("orchestration.orchestrator.run_alignment", side_effect=_write_timeline)
    @patch("orchestration.orchestrator.sf.write")
    @patch("orchestration.orchestrator._run_tts_with_retry")
    def test_successful_run(self, mock_tts, mock_sf, mock_align, mock_storyboard, mock_render, mock_post):
        """Pipeline successfully yields 5 steps and completes."""
        mock_tts.return_value = (24000, [0.0, 0.0])

        gen = orchestrate_video("Hello world today", "voice1", "url")

        states = list(gen)

        # Step 3 yields twice (storyboard, then asset fetch) → 7 total
        texts = [s[0] for s in states]
        assert "Complete" in texts[-1]
        assert states[-1][1].endswith("final.mp4")
        # each stage appears in order
        for stage in ("Step 1/5", "Step 2/5", "Step 3/5", "Step 4/5", "Step 5/5"):
            assert any(stage in t for t in texts), f"missing {stage}"

        mock_tts.assert_called_once()
        mock_sf.assert_called_once()
        mock_align.assert_called_once()
        mock_storyboard.assert_called_once()
        # storyboard receives the timeline DICT, not a path
        assert isinstance(mock_storyboard.call_args[0][0], dict)
        mock_render.assert_called_once()
        mock_post.assert_called_once()

    def test_empty_script(self):
        """Empty script returns error immediately."""
        gen = orchestrate_video("   ", "voice1", "url")
        states = list(gen)
        assert len(states) == 1
        assert "Error: Script is empty" in states[0][0]
        assert states[0][1] is None

    def test_short_script_rejected(self):
        """Scripts under 3 words are rejected before TTS (AUDIO-04)."""
        gen = orchestrate_video("Hi there", "voice1", "url")
        states = list(gen)
        assert len(states) == 1
        assert "too short" in states[0][0]
        assert states[0][1] is None

    @patch("orchestration.orchestrator._run_tts_with_retry", side_effect=Exception("API down"))
    def test_tts_failure_stops_pipeline(self, mock_tts):
        """Exception in TTS stops pipeline after Step 1."""
        gen = orchestrate_video("Hello there friend", "v1", "")
        states = list(gen)

        assert len(states) == 2
        assert "Step 1/5" in states[0][0]
        assert "Error: TTS failed" in states[1][0]
        assert "API down" in states[1][0]

    @patch("orchestration.orchestrator.post_process_video")
    @patch("orchestration.orchestrator.render_video")
    @patch("orchestration.orchestrator.storyboard_pipeline")
    @patch("orchestration.orchestrator.sf.write")
    @patch("orchestration.orchestrator._run_tts_with_retry")
    @patch("orchestration.orchestrator.run_alignment")
    def test_alignment_drift_triggers_fallback(self, mock_align, mock_tts, mock_sf, mock_sb, mock_ren, mock_post):
        """AlignmentDriftError triggers a retry with use_fallback=True."""
        mock_tts.return_value = (24000, [0.0])

        calls = {"n": 0}

        def _drift_then_ok(wav_path, spoken_text, output_path, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise AlignmentDriftError(0.9)
            _write_timeline(wav_path, spoken_text, output_path, **kwargs)

        mock_align.side_effect = _drift_then_ok

        gen = orchestrate_video("Hello there friend", "v1", "")
        states = list(gen)

        texts = [s[0] for s in states]
        assert any("Alignment drift detected" in t for t in texts)
        assert "Complete" in texts[-1]
        for stage in ("Step 1/5", "Step 2/5", "Step 3/5", "Step 4/5", "Step 5/5"):
            assert any(stage in t for t in texts), f"missing {stage}"

        assert mock_align.call_count == 2
        assert mock_align.call_args_list[1][1].get("use_fallback") is True
