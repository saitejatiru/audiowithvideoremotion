"""render/render_bridge.py — Python bridge to Remotion CLI.

Calls `npx remotion render` with timeline.json as --props, validates
the output MP4 exists and has the expected duration (via ffprobe).

This module is consumed by Phase 6's orchestrator.
"""
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the video/ Remotion project (relative to repo root)
VIDEO_PROJECT_DIR = Path(__file__).parent.parent / "video"


class RenderError(Exception):
    """Raised when Remotion render fails."""
    pass


def render_video(
    timeline_path: str,
    output_path: str,
    *,
    composition_id: str = "ExplainerVideo",
    video_dir: str | None = None,
) -> str:
    """Render an explainer video from a timeline.json file.

    Args:
        timeline_path: Path to the timeline.json file.
        output_path: Path for the output MP4 file.
        composition_id: Remotion composition ID (default: "ExplainerVideo").
        video_dir: Override the Remotion project directory.

    Returns:
        The output_path if render succeeds.

    Raises:
        RenderError: If Remotion render fails or output is missing.
        FileNotFoundError: If timeline_path doesn't exist.
    """
    timeline_path = os.path.abspath(timeline_path)
    output_path = os.path.abspath(output_path)
    project_dir = Path(video_dir) if video_dir else VIDEO_PROJECT_DIR

    if not os.path.exists(timeline_path):
        raise FileNotFoundError(f"Timeline not found: {timeline_path}")

    # Read timeline to get expected duration for validation
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)
    expected_duration = timeline.get("audio", {}).get("durationSec", 0)

    # staticFile() only resolves inside video/public/ — copy the narration
    # there and rewrite audio.path to the bare filename.
    public_dir = project_dir / "public"
    audio_src = timeline.get("audio", {}).get("path", "")
    if audio_src and not os.path.isabs(audio_src):
        audio_src = os.path.join(os.path.dirname(timeline_path), audio_src)
    if audio_src and os.path.exists(audio_src):
        public_dir.mkdir(exist_ok=True)
        audio_name = "narration-" + Path(output_path).stem + ".wav"
        shutil.copy2(audio_src, public_dir / audio_name)
        timeline["audio"]["path"] = audio_name

    # Fetched assets sit next to timeline.json → copy into public/ so
    # staticFile() resolves them. Missing file: drop the key so the component
    # falls back to its CSS template (never a broken <Img>/<Video>).
    for scene in timeline.get("scenes", []):
        visual = scene.get("visual", {})
        for key in ("image", "asset"):  # diagram card / background layer
            fname = visual.get(key)
            if not fname:
                continue
            src = os.path.join(os.path.dirname(timeline_path), fname)
            if os.path.exists(src):
                public_dir.mkdir(exist_ok=True)
                shutil.copy2(src, public_dir / fname)
            else:
                visual.pop(key, None)
                if key == "asset":
                    visual.pop("assetKind", None)

    # The composition expects props of shape {timeline: ...}; --props merges
    # the JSON file at top level, so wrap before passing.
    props_fd, props_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(props_fd, "w", encoding="utf-8") as f:
        json.dump({"timeline": timeline}, f)

    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [
        npx, "remotion", "render",
        composition_id,
        output_path,
        "--props", props_path,
    ]

    logger.info("Rendering video: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",      # Remotion prints emoji; default cp1252 on
            errors="replace",      # Windows crashes the stderr reader thread
            timeout=600,  # 10 minute timeout for rendering
        )
    except subprocess.TimeoutExpired:
        raise RenderError("Remotion render timed out after 600 seconds")
    except FileNotFoundError:
        raise RenderError(
            "npx not found — ensure Node.js is installed and in PATH"
        )
    finally:
        os.unlink(props_path)

    if result.returncode != 0:
        logger.error("Remotion stderr: %s", result.stderr)
        raise RenderError(
            f"Remotion render failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    if not os.path.exists(output_path):
        raise RenderError(f"Render completed but output not found: {output_path}")

    # Validate duration if ffprobe is available
    actual_duration = _get_video_duration(output_path)
    if actual_duration is not None and expected_duration > 0:
        # Allow 1-frame tolerance at 30fps (~0.033s)
        tolerance = 0.05
        if abs(actual_duration - expected_duration) > tolerance:
            logger.warning(
                "Duration mismatch: expected %.3fs, got %.3fs (tolerance %.3fs)",
                expected_duration, actual_duration, tolerance,
            )

    logger.info("Render complete: %s (%.1fs)", output_path, actual_duration or 0)
    return output_path


def _get_video_duration(video_path: str) -> float | None:
    """Get video duration via ffprobe. Returns None if ffprobe is unavailable."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, subprocess.TimeoutExpired):
        logger.debug("ffprobe unavailable or failed — skipping duration check")
    return None
