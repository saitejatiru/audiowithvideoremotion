# Requirements: Synced Explainer Video Generator

**Defined:** 2026-07-08
**Core Value:** Narration, on-screen visuals, and captions are perfectly synced to the audio.

## v1 Requirements

### Audio (TTS)

- [ ] **AUDIO-01**: User can input a script and get VibeVoice narration audio back
- [ ] **AUDIO-02**: User can select a voice, including an Indian voice
- [ ] **AUDIO-03**: User can clone a voice from a short reference clip
- [ ] **AUDIO-04**: Script is normalized (numbers/symbols/code) before synthesis, keeping a raw→spoken map for captions
- [ ] **AUDIO-05**: The cloned reference voice (the Indian voice created in Colab) is saved and reused as the default speaker for all generated audio

### Alignment (Sync)

- [ ] **ALIGN-01**: System produces word-level timestamps by forced-aligning the known script to the audio (WhisperX)
- [ ] **ALIGN-02**: System verifies TTS fidelity via ASR-WER and flags/regenerates when drift exceeds a threshold
- [ ] **ALIGN-03**: System emits `timeline.json` (words, sentences, durations, speaker) as the canonical contract
- [ ] **ALIGN-04**: System falls back to whisper-timestamped when forced alignment fails

### Storyboard (LLM)

- [ ] **STORY-01**: LLM generates a per-sentence storyboard (visual, on-screen text, scene) from script + sentences
- [ ] **STORY-02**: Storyboard output is schema-validated JSON with a repair/fallback path
- [ ] **STORY-03**: Scene boundaries clamp to sentence boundaries (a scene never straddles a word)

### Video (Remotion)

- [ ] **VIDEO-01**: Remotion renders a video from `timeline.json`, synced to the narration audio
- [ ] **VIDEO-02**: Word-level captions render in-video, timed to each word's start/end
- [ ] **VIDEO-03**: Composition duration derives from actual audio length (no cutoff or drift)
- [ ] **VIDEO-04**: Multi-speaker captions are visually distinguished when the audio has multiple speakers

### Post-processing

- [ ] **POST-01**: Output video metadata is stripped/de-fingerprinted (ffmpeg `-map_metadata -1`)
- [ ] **POST-02**: Output stays web-playable (faststart) and plays correctly after stripping

### Platform

- [ ] **PLAT-01**: Simple Gradio page — enter script, pick voice, generate, preview/download the video
- [ ] **PLAT-02**: Orchestration runs the full multi-stage pipeline end-to-end with basic retry

### Infrastructure

- [ ] **INFRA-01**: GPU stages (TTS, alignment) run behind a stable HTTP contract — **free-tier Colab** now (note its limits: ephemeral URL, ~90-min idle timeout, daily GPU caps), swappable to Modal/RunPod

## v2 Requirements

### Scale
- **SCALE-01**: Job queue for concurrent users / GPU contention
- **SCALE-02**: Persistent hosting with a permanent URL

### Media
- **MEDIA-01**: Automatic b-roll / stock imagery sourcing for scenes
- **MEDIA-02**: Emotion presets for narration delivery

### Bot
- **BOT-01**: Telegram bot to submit a script and receive the finished video

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time / streaming generation | Batch is fine for explainer videos; adds large complexity |
| Manual video-editor UI | v1 is auto-generated only |
| Accounts / billing / multi-tenant | Prototype, not a product yet |
| Explicit emotion-control knob | Expressiveness comes from text + reference clip, not a parameter |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (pending roadmap) | | |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 20 ⚠️

---
*Requirements defined: 2026-07-08*
*Last updated: 2026-07-08 after initial definition*
