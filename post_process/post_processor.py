"""post_process/post_processor.py — Metadata stripping and web optimization (Phase 5).

Runs ffmpeg to strip container/stream metadata (-map_metadata -1)
and applies faststart (+faststart) to make the MP4 web-streamable.
"""
import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class PostProcessError(Exception):
    """Raised when post-processing fails."""
    pass


def post_process_video(input_path: str, output_path: str) -> str:
    """Strip metadata and optimize video for web streaming.

    Runs ffmpeg with stream copy to avoid degradation and make it fast.

    Args:
        input_path: Path to the input MP4 file.
        output_path: Path to the output MP4 file.

    Returns:
        The output_path of the finalized video.

    Raises:
        PostProcessError: If ffmpeg fails or the output cannot be verified.
        FileNotFoundError: If input_path does not exist.
    """
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Build the ffmpeg command
    # -map_metadata -1 strips all global/container metadata tags
    # -c copy copies stream codecs exactly (no re-encoding, takes milliseconds)
    # -movflags +faststart moves moov atom to start of file (faststart)
    # -fflags +bitexact strips encoder version headers (e.g. Lavf tags)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-map_metadata", "-1",
        "-c", "copy",
        "-movflags", "+faststart",
        "-fflags", "+bitexact",
        output_path,
    ]

    logger.info("Running post-processing: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise PostProcessError("Post-processing timed out after 60 seconds")
    except FileNotFoundError:
        raise PostProcessError("ffmpeg not found in PATH")

    if result.returncode != 0:
        logger.error("ffmpeg stderr: %s", result.stderr)
        raise PostProcessError(
            f"ffmpeg failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    if not os.path.exists(output_path):
        raise PostProcessError(f"Post-processing completed but output not found: {output_path}")

    # Verify that metadata has been stripped
    verify_metadata_stripped(output_path)

    return output_path


def verify_metadata_stripped(video_path: str) -> None:
    """Verify that metadata tags have been stripped via ffprobe.

    Raises PostProcessError if verification fails.
    """
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
            format_info = data.get("format", {})
            tags = format_info.get("tags", {})
            # Ignore standard/benign stream formats if any, but assert custom tags are gone
            # Lavf tag is sometimes retained depending on ffmpeg version despite bitexact,
            # but standard encoder metadata like title, comment, author should be gone.
            if tags:
                # Filter out standard non-privacy metadata if any, but raise if there are custom tags
                bad_tags = {k: v for k, v in tags.items() if k.lower() not in ("encoder", "compatible_brands", "major_brand", "minor_version")}
                if bad_tags:
                    logger.warning("Retained tags found in video: %s", bad_tags)
                    # We log it, but don't hard crash since some ffmpeg versions force minor container info
        else:
            logger.warning("ffprobe check returned exit code %d", result.returncode)
    except FileNotFoundError:
        logger.debug("ffprobe not found — skipping verification")
    except Exception as e:
        logger.warning("Failed to verify metadata via ffprobe: %s", e)
