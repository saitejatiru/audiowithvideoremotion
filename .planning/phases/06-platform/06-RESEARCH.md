# Phase 6: Platform - Research

**Researched:** 2026-07-09
**Domain:** Gradio / Pipeline Orchestration
**Confidence:** HIGH

## Summary

Phase 6 ties the entire Python and Node.js pipeline together behind a single Gradio interface. It handles retries for transient Colab GPU failures and orchestrates the steps.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PLAT-01 | Single Gradio page, script-in/video-out | `gr.Interface` with async generator |
| PLAT-02 | Pipeline sequence + transient retries | Python `tenacity` library for robust retries |

---

## Standard Stack

| Library | Version | Purpose |
|---------|---------|---------|
| gradio | >= 4.0 | Web UI |
| tenacity | latest | Exponential backoff for transient HTTP errors |

## Architecture Patterns

### Pattern 1: The Orchestrator
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class PipelineOrchestrator:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _run_tts(self, text, voice):
        # Calls Phase 1
        pass
        
    def generate_video(self, script, voice):
        yield "Generating audio..."
        audio_path = self._run_tts(script, voice)
        
        yield "Aligning..."
        timeline = self._run_alignment(audio_path, script)
        
        yield "Storyboarding..."
        timeline = self._run_storyboard(timeline)
        
        yield "Rendering video..."
        video_path = self._run_render(timeline)
        
        yield "Finalizing..."
        final_video = self._run_post_processing(video_path)
        
        yield final_video
```

### Pattern 2: Gradio Generator UI
Use a generator function so the Gradio UI updates the user with intermediate states (e.g., "Generating audio...", "Aligning...").

## Anti-Patterns to Avoid
- **Blocking the UI thread:** The pipeline operations take time (especially rendering). Always run the pipeline asynchronously or use Gradio's queuing.
- **Leaking intermediate files:** Clean up the intermediate `timeline.json` and raw MP4s, or store them in a temporary `run_id` directory to prevent parallel requests from overwriting each other.

## Open Questions
- Concurrency: Should Gradio support multiple users on Colab? Colab has limited memory; it's recommended to restrict Gradio `concurrency_limit` to 1.
