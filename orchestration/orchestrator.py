"""platform/orchestrator.py — Phase 6: Full pipeline orchestrator.

Runs the end-to-end pipeline:
TTS -> Align -> Storyboard -> Render -> Post-process

Handles transient failures via tenacity and yields progress updates for Gradio.
"""
import json
import os
import shutil
import tempfile
import traceback
import logging

import soundfile as sf
from tenacity import retry, stop_after_attempt, wait_exponential

from tts.normalizer import normalize
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
    """Return (sample_rate, audio_data). Uses the Colab HTTP endpoint when
    backend_url is set (INFRA-01 contract), else the local model."""
    if backend_url:
        import io
        import requests

        resp = requests.post(
            backend_url.rstrip("/") + "/synthesize",
            json={"text": text, "speaker_id": voice},
            headers={"Authorization": "Bearer " + os.environ.get("API_SECRET", "")},
            timeout=600,
        )
        resp.raise_for_status()
        audio_data, sample_rate = sf.read(io.BytesIO(resp.content))
        return sample_rate, audio_data
    return 24000, run_vibevoice(text, voice)


def orchestrate_video(
    script: str,
    voice: str,
    backend_url: str,
    video_format: str = "16:9",
    subject: str = "Auto-detect",
    grade: str = "Auto-detect",
    style: str = "Whiteboard (scribe)",
    animate_first: bool = True,
):
    """Generator that runs the full pipeline and yields progress updates.

    Yields:
        tuple: (status_text: str, final_video_path: str or None)
    """
    script = script.strip()
    if not script:
        yield "Error: Script is empty.", None
        return

    # AUDIO-04: expand numbers/symbols before TTS; spoken form feeds both
    # synthesis and forced alignment, word_map keeps raw text for captions.
    try:
        spoken, word_map = normalize(script)
    except ValueError as e:
        yield f"Error: {e}", None
        return

    # FAIL FAST: verify the LLM key NOW, before the slow TTS/align/Manim.
    # A bad key used to surface only at the storyboard step — after ~25 min of
    # wasted compute. This 2-second ping catches 401/expired/out-of-credits up front.
    yield "Step 0/5: Checking LLM key...", None
    try:
        from storyboard.client import call_llm
        call_llm([{"role": "user", "content": "ping"}])
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            hint = (
                "401 Unauthorized — your LLM key is invalid, expired, or out of free "
                "credits.\n"
                " • Re-check cell 2 printed 'LLM OK' with the SAME key, and RESTART "
                "cell 8 (app.py) after changing keys — a running app keeps the old key.\n"
                " • If cell 2 says OK but this fails, the app has a stale key: re-run cell 8.\n"
                " • NVIDIA free credits can run out — regenerate a key at build.nvidia.com, "
                "or switch to Groq (free, reliable): base https://api.groq.com/openai/v1, "
                "model llama-3.3-70b-versatile, key from console.groq.com."
            )
        else:
            hint = f"LLM call failed: {msg}"
        yield f"Error: LLM check failed before generation.\n{hint}", None
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
            sample_rate, audio_data = _run_tts_with_retry(spoken, voice, backend_url)
        except Exception as e:
            logger.error("TTS failed: %s", traceback.format_exc())
            yield f"Error: TTS failed after retries — {e}", None
            return

        sf.write(audio_path, audio_data, sample_rate)

        # Step 2: Align
        yield "Step 2/5: Aligning audio with script...", None
        try:
            run_alignment(audio_path, spoken, timeline_path)
        except AlignmentDriftError as e:
            logger.warning("Alignment drift detected (WER=%f). Retrying with fallback.", e.wer_score)
            yield "Step 2/5: Alignment drift detected. Retrying with robust fallback...", None
            try:
                run_alignment(audio_path, spoken, timeline_path, use_fallback=True)
            except Exception as e2:
                yield f"Error: Alignment fallback failed — {e2}", None
                return
        except Exception as e:
            logger.error("Align failed: %s", traceback.format_exc())
            yield f"Error: Alignment failed — {e}", None
            return

        # Step 3: Storyboard
        try:
            with open(timeline_path, "r", encoding="utf-8") as f:
                t_data = json.load(f)
            meta = t_data.get("meta", {})
            yield (
                "Step 3/5: Generating storyboard (LLM)... "
                f"[align: {meta.get('alignMethod', '?')}, wer: {meta.get('wer', '?')}]"
            ), None
            # We don't retry LLM here, the storyboard pipeline handles its own repairs.
            storyboard_pipeline(t_data, subject=subject, grade=grade, animate_first=animate_first)
        except Exception as e:
            logger.error("Storyboard failed: %s", traceback.format_exc())
            yield f"Error: Storyboard generation failed — {e}", None
            return

        if t_data.get("meta", {}).get("storyboard") == "fallback":
            # Refuse to burn a 10-minute render on a degraded storyboard.
            # ALLOW_PLAIN_VIDEO=1 renders anyway using heuristic scenes.
            err = t_data["meta"].get("storyboardError", "unknown")
            if not os.environ.get("ALLOW_PLAIN_VIDEO"):
                yield (
                    f"Error: LLM storyboard FAILED — {err}\n"
                    "Not rendering a degraded video. Fix cell 2 in the Colab notebook "
                    "(it must print 'LLM OK'), then regenerate. To render anyway with "
                    "heuristic scenes, set ALLOW_PLAIN_VIDEO=1 and restart app.py."
                ), None
                return
            yield f"WARNING: LLM storyboard failed ({err}) — rendering heuristic scenes.", None

        # Render Manim 2D animations for 'animation' scenes (Physics/Maths).
        # Slow + can fail → fail-soft to bullet inside. Runs before asset fetch
        # so a rendered clip claims the scene's visual.
        yield "Step 3/5: Rendering 2D animations (Manim)...", None
        try:
            from storyboard.manim_gen import render_manim_scenes
            render_manim_scenes(t_data, run_dir)
        except Exception:
            logger.warning("Manim render skipped: %s", traceback.format_exc())

        # Fetch real visuals per scene: Wikimedia diagrams + Pixabay
        # illustrations/video (per-scene no-ops on failure; belt-and-suspenders
        # try so it can never kill the pipeline)
        yield "Step 3/5: Fetching illustrations & diagrams...", None
        try:
            from storyboard.assets import fetch_scene_assets
            fetch_scene_assets(t_data, run_dir)
        except Exception:
            logger.warning("Asset fetch skipped: %s", traceback.format_exc())

        # Inject user-selected format/style + raw→spoken word map into timeline meta
        t_data.setdefault("meta", {})["format"] = video_format
        t_data["meta"]["style"] = "whiteboard" if style.lower().startswith("white") else "dark"
        if word_map:
            t_data["meta"]["wordMap"] = word_map
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

        # Save a STABLE copy the user can actually grab. The render lives in a
        # temp dir (auto-deleted) and the Colab iframe proxy can't reliably serve
        # video for playback/download — so copy it out to Google Drive (mounted)
        # where it just appears in the user's Drive, no proxy needed.
        saved_path, where = final_path, "the run dir"
        try:
            import datetime
            drive_dir = "/content/drive/MyDrive/explainer_videos"
            content_dir = "/content/explainer_videos"
            out_base = drive_dir if os.path.isdir("/content/drive/MyDrive") else content_dir
            os.makedirs(out_base, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(out_base, f"video_{stamp}.mp4")
            shutil.copy2(final_path, dest)  # only adopt the new path if this succeeds
            saved_path = dest
            where = ("Google Drive → explainer_videos"
                     if out_base == drive_dir else "/content/explainer_videos (Colab file panel)")
        except Exception:
            logger.warning("Could not save output copy: %s", traceback.format_exc())

        # Done
        yield f"Complete! Saved to {where}: {os.path.basename(saved_path)}", saved_path

    except Exception as e:
        logger.error("Unexpected error in pipeline: %s", traceback.format_exc())
        yield f"Error: An unexpected failure occurred — {e}", None
        return
