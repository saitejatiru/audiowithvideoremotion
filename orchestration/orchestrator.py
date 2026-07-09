"""platform/orchestrator.py — Phase 6: Full pipeline orchestrator.

Runs the end-to-end pipeline:
TTS -> Align -> Storyboard -> Render -> Post-process

Handles transient failures via tenacity and yields progress updates for Gradio.
"""
import os
import tempfile
import traceback
import logging

import soundfile as sf
from tenacity import retry, stop_after_attempt, wait_exponential

from tts.server import run_vibevoice
from align.align_pipeline import run_alignment, AlignmentDriftError
from storyboard.pipeline import storyboard_pipeline
from render.render_bridge import render_video
from post_process.post_processor import post_process_video

logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Raised when the pipeline fails after retries."""
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def _run_tts_with_retry(text: str, voice: str, backend_url: str) -> tuple:
    """Run TTS with exponential backoff for transient HTTP errors."""
    return run_vibevoice(text, voice, backend_url)


def orchestrate_video(script: str, voice: str, backend_url: str, video_format: str = "16:9"):
    """Generator that runs the full pipeline and yields progress updates.

    Yields:
        tuple: (status_text: str, final_video_path: str or None)
    """
    script = script.strip()
    if not script:
        yield "Error: Script is empty.", None
        return

    # Create a unique temporary directory for this run's artifacts
    temp_dir_obj = tempfile.TemporaryDirectory(prefix="vibevoice_run_")
    run_dir = temp_dir_obj.name

    audio_path = os.path.join(run_dir, "audio.wav")
    timeline_path = os.path.join(run_dir, "timeline.json")
    rendered_path = os.path.join(run_dir, "rendered.mp4")
    final_path = os.path.join(run_dir, "final.mp4")

    try:
        # Step 1: TTS
        yield "Step 1/5: Generating audio (TTS)...", None
        try:
            sample_rate, audio_data = _run_tts_with_retry(script, voice, backend_url)
        except Exception as e:
            logger.error("TTS failed: %s", traceback.format_exc())
            yield f"Error: TTS failed after retries — {e}", None
            return

        sf.write(audio_path, audio_data, sample_rate)

        # Step 2: Align
        yield "Step 2/5: Aligning audio with script...", None
        try:
            run_alignment(audio_path, script, timeline_path)
        except AlignmentDriftError as e:
            logger.warning("Alignment drift detected (WER=%f). Retrying with fallback.", e.wer_score)
            yield "Step 2/5: Alignment drift detected. Retrying with robust fallback...", None
            try:
                run_alignment(audio_path, script, timeline_path, use_fallback=True)
            except Exception as e2:
                yield f"Error: Alignment fallback failed — {e2}", None
                return
        except Exception as e:
            logger.error("Align failed: %s", traceback.format_exc())
            yield f"Error: Alignment failed — {e}", None
            return

        # Step 3: Storyboard
        yield "Step 3/5: Generating storyboard (LLM)...", None
        try:
            # We don't retry LLM here, the storyboard pipeline handles its own repairs.
            storyboard_pipeline(timeline_path, timeline_path)
        except Exception as e:
            logger.error("Storyboard failed: %s", traceback.format_exc())
            yield f"Error: Storyboard generation failed — {e}", None
            return
            
        # Inject the user-selected video format into the timeline meta
        import json
        with open(timeline_path, "r", encoding="utf-8") as f:
            t_data = json.load(f)
        if "meta" not in t_data:
            t_data["meta"] = {}
        t_data["meta"]["format"] = video_format
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump(t_data, f, indent=2)

        # Step 4: Render
        yield "Step 4/5: Rendering video with Remotion...", None
        try:
            # render_bridge spawns npx remotion render
            render_video(timeline_path, rendered_path)
        except Exception as e:
            logger.error("Render failed: %s", traceback.format_exc())
            yield f"Error: Video rendering failed — {e}", None
            return

        # Step 5: Post-process
        yield "Step 5/5: Post-processing (stripping metadata, optimizing for web)...", None
        try:
            post_process_video(rendered_path, final_path)
        except Exception as e:
            logger.error("Post-process failed: %s", traceback.format_exc())
            yield f"Error: Post-processing failed — {e}", None
            return

        # Done
        yield "Complete! Video generated successfully.", final_path

    except Exception as e:
        logger.error("Unexpected error in pipeline: %s", traceback.format_exc())
        yield f"Error: An unexpected failure occurred — {e}", None
        return
