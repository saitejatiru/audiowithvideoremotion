# Roadmap: Synced Explainer Video Generator

## Overview

Six phases building from foundation to finished product: a stable GPU-backed TTS service and
data contract (Phase 1), deterministic word-level sync engine (Phase 2), LLM storyboard (Phase 3),
Remotion video render (Phase 4), metadata clean-up (Phase 5), and a Gradio platform that ties the
full pipeline together (Phase 6). The critical path is Phase 2 — sync is the make-or-break
capability and must be verified in isolation before any video work begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Contracts & Text Prep** - GPU HTTP endpoint live, script normalizer running, timeline.json schema defined, default voice persisted (completed 2026-07-09)
- [ ] **Phase 2: Alignment Engine** - Word-level timestamps from forced alignment, ASR-WER guard, timeline.json emitted
- [x] **Phase 3: Storyboard** - LLM generates schema-validated scene content per sentence (completed 2026-07-09)
- [ ] **Phase 4: Remotion Render** - Video synced to audio with word-level captions and correct duration
- [ ] **Phase 5: Post-processing** - Metadata stripped, output web-ready
- [ ] **Phase 6: Platform** - Gradio UI + orchestrator runs the full pipeline end-to-end

## Phase Details

### Phase 1: Contracts & Text Prep
**Goal**: TTS produces narration audio from a normalized script via a stable GPU HTTP endpoint; the default Indian voice is persisted and reusable across sessions; the timeline.json schema is documented as the canonical inter-stage contract.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-04, AUDIO-05
**Success Criteria** (what must be TRUE):
  1. User can POST a script to the GPU HTTP endpoint and receive a WAV file in return; the endpoint URL is the only thing that changes when switching from Colab to Modal/RunPod
  2. User can choose from available voices including at least one Indian voice before generating audio
  3. User can supply a short reference clip and clone a voice; the cloned Indian voice is saved to disk and reused as the default speaker on all subsequent generations without re-upload
  4. Numbers, symbols, URLs, and short inputs (under ~3 words) in the script are expanded or rejected before TTS; the raw→spoken word map is preserved alongside the spoken text for caption use
  5. Running two generations back-to-back produces audio from the same persisted default voice without any manual selection
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — TDD test scaffold: conftest.py + test stubs for all INFRA-01/AUDIO-01..05 requirements (RED state)
- [ ] 01-02-PLAN.md — Normalizer + Schema: text normalizer (AUDIO-04) + timeline.json Pydantic schema contract
- [ ] 01-03-PLAN.md — TTS Service: FastAPI server + voice store + cloudflared Colab launch (INFRA-01, AUDIO-01..03, AUDIO-05)

### Phase 2: Alignment Engine
**Goal**: Word-level timestamps are forced-aligned against the known spoken script, verified by ASR-WER, and emitted as the canonical timeline.json that every downstream stage reads. This phase must be verified with a real clip before Phase 4 begins.
**Depends on**: Phase 1
**Requirements**: ALIGN-01, ALIGN-02, ALIGN-03, ALIGN-04
**Success Criteria** (what must be TRUE):
  1. Given a WAV file and the spoken (normalized) script, the system produces per-word start/end timestamps using WhisperX forced alignment
  2. The system computes ASR-WER after alignment and automatically flags or regenerates audio when drift exceeds the configured threshold
  3. A valid timeline.json is written containing words[], sentences[], audio metadata (path, sampleRate, durationSec), and a wer field — all fields matching the defined schema
  4. When forced alignment fails outright, the system transparently falls back to whisper-timestamped and still produces a complete timeline.json without crashing
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Test scaffold: conftest.py + test stubs for all ALIGN-XX requirements (RED state)
- [ ] 02-02-PLAN.md — Aligner + Schema: WhisperX forced alignment (ALIGN-01) + timeline.json builder (ALIGN-03)
- [ ] 02-03-PLAN.md — WER Guard + Fallback: ASR-WER verifier (ALIGN-02) + whisper-timestamped adapter (ALIGN-04)
- [x] 02-04-PLAN.md — Pipeline integration + isolation verification gate before Phase 4

### Phase 3: Storyboard
**Goal**: LLM produces validated per-sentence scene content (visual type, on-screen text, keyword) whose timing is clamped entirely to sentence boundaries from timeline.json — the LLM never sets durations.
**Depends on**: Phase 2
**Requirements**: STORY-01, STORY-02, STORY-03
**Success Criteria** (what must be TRUE):
  1. Given the normalized script and sentences[] from timeline.json, the LLM returns a scenes[] array with visual type, keyword/query, and on-screen text for each sentence group
  2. The scenes[] output passes schema validation; one repair retry runs on parse failure; a deterministic bullet-from-sentences fallback activates when repair also fails — generation never crashes on bad LLM output
  3. Every scene's start/end is derived from sentence-aligned timestamps from timeline.json; no scene boundary falls mid-word or between two words in the same sentence
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Schema + test scaffold: LLMSceneItem, LLMScenesResponse, TimelineScene (12 passed)
- [x] 03-02-PLAN.md — Prompter + Client: system prompt with embedded schema, OpenAI-compatible client
- [x] 03-03-PLAN.md — Repair + Fallback: three-layer defense (strict → json-repair → bullet fallback)
- [x] 03-04-PLAN.md — Pipeline integration: storyboard_pipeline + inject_timing

### Phase 4: Remotion Render
**Goal**: Remotion consumes timeline.json and renders a synced MP4 — narration audio embedded, scenes switching at sentence boundaries, word-level captions frame-accurate, total duration matching the actual audio length.
**Depends on**: Phase 3
**Requirements**: VIDEO-01, VIDEO-02, VIDEO-03, VIDEO-04
**Success Criteria** (what must be TRUE):
  1. Running the Remotion composition with timeline.json as props produces an MP4 where on-screen visuals change at scene boundaries aligned to the narration audio
  2. Word-level captions appear and disappear frame-accurately — each word's display window matches its start/end timestamps in timeline.json
  3. The rendered video's total duration matches the actual audio duration to within one frame (ceil(durationSec * fps)); no cutoff or trailing silence
  4. When the audio contains multiple speakers, captions for each speaker are visually distinct (different color or position)
**Plans**: TBD

### Phase 5: Post-processing
**Goal**: The rendered MP4 is stripped of all container and stream-level metadata and fingerprints, and remains correctly web-streamable after stripping.
**Depends on**: Phase 4
**Requirements**: POST-01, POST-02
**Success Criteria** (what must be TRUE):
  1. The ffmpeg strip command removes all container and stream-level metadata tags from the rendered MP4 (ffprobe on the output shows no tags)
  2. The stripped MP4 plays correctly in a browser, loads without seeking delays, and has the moov atom at the file head (faststart confirmed)
**Plans**: TBD

### Phase 6: Platform
**Goal**: A single Gradio page accepts a script, selects a voice, and runs the full normalize→TTS→align→storyboard→render→strip pipeline end-to-end with automatic retry on transient failures.
**Depends on**: Phase 5
**Requirements**: PLAT-01, PLAT-02
**Success Criteria** (what must be TRUE):
  1. User enters a script into the Gradio page, picks a voice, clicks Generate, and receives a previewable and downloadable finished video without any CLI interaction
  2. If a pipeline stage fails transiently (Colab session timeout, network error), the orchestrator retries that stage automatically before surfacing an error to the user
  3. The orchestrator runs all pipeline stages in the correct sequence with a single trigger and surfaces a clear error message if a stage fails after retries
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Contracts & Text Prep | 3/3 | Complete   | 2026-07-09 |
| 2. Alignment Engine | 4/4 | Code complete — Colab gate pending | 2026-07-09 |
| 3. Storyboard | 4/4 | Code complete — LLM test needs API key | 2026-07-09 |
| 4. Remotion Render | 0/TBD | Not started | - |
| 5. Post-processing | 0/TBD | Not started | - |
| 6. Platform | 0/TBD | Not started | - |
