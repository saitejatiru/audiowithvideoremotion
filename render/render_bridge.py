"""render/render_bridge.py — Python bridge to Remotion CLI.

Calls `npx remotion render` with timeline.json as --props, validates
the output MP4 exists and has the expected duration (via ffprobe).

This module is consumed by Phase 6's orchestrator.
"""
import json
import logging
import os
import subprocess
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

    # Build the render command
    # --props takes a file path; Remotion reads it as inputProps
    cmd = [
        "npx", "remotion", "render",
        composition_id,
        output_path,
        "--props", timeline_path,
    ]

    logger.info("Rendering video: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for rendering
        )
    except subprocess.TimeoutExpired:
        raise RenderError("Remotion render timed out after 600 seconds")
    except FileNotFoundError:
        raise RenderError(
            "npx not found — ensure Node.js is installed and in PATH"
        )

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
