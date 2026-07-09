# Phase 5: Post-processing - Research

**Researched:** 2026-07-09
**Domain:** ffmpeg / Video metadata stripping / faststart
**Confidence:** HIGH

## Summary

Phase 5 strips metadata from the rendered MP4 to ensure privacy, remove fingerprints, and optimizes it for web playback by moving the `moov` atom to the front (faststart).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POST-01 | Strip container and stream-level metadata | `ffmpeg -map_metadata -1 -fflags +bitexact` |
| POST-02 | Web streamable (faststart) | `ffmpeg -movflags +faststart` |

---

## Standard Stack

| Tool | Version | Purpose |
|------|---------|---------|
| ffmpeg | latest | Video processing CLI |

## Architecture Patterns

### Pattern 1: FFmpeg Strip Command
To completely strip metadata and ensure web streaming:
```bash
ffmpeg -i input.mp4 -map_metadata -1 -c:v copy -c:a copy -movflags +faststart -fflags +bitexact output.mp4
```

- `-map_metadata -1`: Removes global metadata.
- `-c:v copy -c:a copy`: Avoids re-encoding, ensuring this step takes milliseconds.
- `-movflags +faststart`: Moves `moov` atom to head for streaming.
- `-fflags +bitexact`: Removes FFmpeg's own Lavf version tags.

## Anti-Patterns to Avoid
- **Re-encoding:** Do not omit `-c copy` as it will unnecessarily degrade quality and take a long time to process.

## Open Questions
- Is `ffprobe` required for verification in tests? Yes, we can parse `ffprobe -v quiet -print_format json -show_format` to assert tags are empty.
