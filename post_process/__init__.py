"""post_process/ — Phase 5: Video post-processing.

Exports:
    post_process_video  — strip metadata + add faststart
    PostProcessError    — raised on process failure
"""
from post_process.post_processor import post_process_video, PostProcessError

__all__ = ["post_process_video", "PostProcessError"]
