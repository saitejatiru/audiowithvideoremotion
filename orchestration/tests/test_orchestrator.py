"""Tests for platform/orchestrator.py.

Verifies the generator sequence and failure handling by mocking all external module dependencies.
"""
from unittest.mock import patch, MagicMock

from orchestration.orchestrator import orchestrate_video
from align.align_pipeline import AlignmentDriftError


class TestOrchestrateVideo:
    """Tests the orchestrate_video generator."""

    @patch("orchestration.orchestrator.post_process_video")
    @patch("orchestration.orchestrator.render_video")
    @patch("orchestration.orchestrator.storyboard_pipeline")
    @patch("orchestration.orchestrator.run_alignment")
    @patch("orchestration.orchestrator.sf.write")
    @patch("orchestration.orchestrator._run_tts_with_retry")
    def test_successful_run(self, mock_tts, mock_sf, mock_align, mock_storyboard, mock_render, mock_post):
        """Pipeline successfully yields 5 steps and completes."""
        mock_tts.return_value = (24000, [0.0, 0.0])
        
        gen = orchestrate_video("Hello world", "voice1", "url")
        
        states = list(gen)
        
        # Expect 5 steps + 1 completion = 6 yields
        assert len(states) == 6
        assert "Step 1/5" in states[0][0]
        assert "Step 2/5" in states[1][0]
        assert "Step 3/5" in states[2][0]
        assert "Step 4/5" in states[3][0]
        assert "Step 5/5" in states[4][0]
        assert "Complete" in states[5][0]
        assert states[5][1].endswith("final.mp4")

        mock_tts.assert_called_once()
        mock_sf.assert_called_once()
        mock_align.assert_called_once()
        mock_storyboard.assert_called_once()
        mock_render.assert_called_once()
        mock_post.assert_called_once()

    def test_empty_script(self):
        """Empty script returns error immediately."""
        gen = orchestrate_video("   ", "voice1", "url")
        states = list(gen)
        assert len(states) == 1
        assert "Error: Script is empty" in states[0][0]
        assert states[0][1] is None

    @patch("orchestration.orchestrator._run_tts_with_retry", side_effect=Exception("API down"))
    def test_tts_failure_stops_pipeline(self, mock_tts):
        """Exception in TTS stops pipeline after Step 1."""
        gen = orchestrate_video("Hello", "v1", "")
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
        
        # First call raises drift, second call succeeds
        mock_align.side_effect = [AlignmentDriftError(0.9), None]
        
        gen = orchestrate_video("Hello", "v1", "")
        states = list(gen)
        
        assert len(states) == 7
        assert "Step 1/5" in states[0][0]
        assert "Step 2/5" in states[1][0]
        assert "Alignment drift detected" in states[2][0]
        assert "Step 3/5" in states[3][0]
        assert "Step 4/5" in states[4][0]
        assert "Step 5/5" in states[5][0]
        assert "Complete" in states[6][0]
        
        assert mock_align.call_count == 2
        assert mock_align.call_args_list[1][1].get("use_fallback") is True
