# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-08)

**Core value:** Narration, on-screen visuals, and captions are perfectly synced to the audio.
**Current focus:** Phase 5 — Post-processing (code complete)

## Current Position

Phase: 6 of 6 (Platform)
Plan: 2 of 2 in current phase
Status: All 6 phases code complete — orchestrator/render integration seams fixed; Colab E2E verification pending
Last activity: 2026-07-09 — Fixed 5 integration bugs found in post-Antigravity review (see Decisions below)

Progress: [████████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 3 min
- Total execution time: 0.26 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-contracts-text-prep | 3 | 9 min | 3 min |
| 02-alignment-engine | 4 | 13 min | 3.25 min |
| 03-storyboard | 4 | 7 min | 1.75 min |
| 04-remotion-render | 3 | 6 min | 2 min |
| 05-post-processing | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 4 min, 2 min, 3 min, 3 min, 3 min
- Trend: fast

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Design: GPU stage is a swappable HTTP endpoint (Colab now, Modal/RunPod later) — INFRA-01
- Design: WhisperX forced alignment is primary; whisper-timestamped is fallback; ASR-WER guard is mandatory
- Design: LLM sets scene content only; forced alignment sets all timing — LLM never sets durations
- Design: Captions rendered inside Remotion, not burned in post
- Platform: Extend existing Gradio app (VibeVoice/app.py)
- TDD RED pattern (01-01): imports deferred into test bodies so --collect-only works on Windows without ImportError
- TDD RED pattern (01-01): stdlib struct used for WAV fixture — no soundfile dep in RED state
- TDD RED pattern (01-01): pytestmark skipif(Windows) on test_normalizer.py (pynini unavailable on Windows)
- Schema (01-02): write_phase1_timeline() derives durationSec via soundfile.info() internally — invariant enforced in code, not docs
- Normalizer (01-02): NeMo import guarded; returns (raw_text, []) on Windows; Phase 2 spoken-form contract documented in module docstring
- Server (01-03): run_vibevoice lazy-loaded inside endpoint — server.py imports on Windows without GPU/vibevoice package
- Server (01-03): _check_auth reads API_SECRET at call time so monkeypatch.setenv works in tests
- VoiceStore (01-03): ponytail AUDIO-03 — 0.5B stores reference audio only; true voice conditioning needs 1.5B fork
- TDD RED pattern (02-01): xfail(strict=False) used throughout — xpass won't fail suite when implementation arrives
- TDD RED pattern (02-01): real_wav_path uses pytest.skip (not xfail) — aligner/verifier tests show SKIPPED on Windows (correct)
- TDD RED pattern (02-01): soundfile+librosa available on Windows — synthetic_wav fixture runs natively without importorskip guard
- Aligner (02-02): whisperx import guarded inside function body — align.aligner imports cleanly on Windows without whisperx/GPU
- Schema (02-02): build_timeline() reuses tts.schema Pydantic models (Timeline etc.), returns model_dump() — no forked duplicate (I-02)
- Schema (02-02): durationSec from librosa.get_duration(path=) enforced in code; soundfile.info() for sampleRate (both header-only reads)
- Verifier (02-03): heavy imports (whisper, jiwer, whisper_normalizer) deferred inside compute_wer() — module loads on Windows without GPU
- Verifier (02-03): EnglishTextNormalizer lazy-inited as global _normalizer inside compute_wer() body (avoids grep false-positive from helper fn name)
- Fallback (02-03): whisper_timestamped guarded inside fallback_align() body; nan_ratio() exported for pipeline's structural failure detection
- Pipeline (02-04): AlignmentDriftError raised (not silent fallback) on WER > threshold — Phase 6 catches and retries TTS once, then calls use_fallback=True
- Pipeline (02-04): NaN ratio check runs before WER guard — avoids wasted Whisper inference on structurally broken alignment
- Pipeline (02-04): Phase 4 BLOCKED until isolation_test.py passes on Colab GPU with TEST_CLIP_PATH set
- Schema (03-01): LLMSceneItem uses extra='ignore' to silently drop hallucinated timing fields from LLM
- Schema (03-01): TimelineScene enforces timing injection from sentences[] — LLM never sets start/end
- Prompter (03-02): System prompt embeds model_json_schema() and includes 'json' keyword for DeepSeek compatibility
- Client (03-02): openai import deferred inside call_llm() body — storyboard/ imports cleanly without openai package
- Repair (03-03): Three-layer defense: strict json.loads → json-repair → deterministic bullet fallback; never raises
- Pipeline (03-04): call_llm imported at pipeline module level (deferred openai import is inside client.py); enables mock.patch in tests
- Render (04-01): Remotion Composition generic types cast to any to bypass strict Zod Schema compilation constraints
- Render (04-02): SceneRenderer + CaptionRenderer map current playback time from useCurrentFrame() / fps (STORY-03)
- Render (04-02): CaptionRenderer maps speaker indices to cyan/amber/etc. colors (VIDEO-04)
- Render (04-03): render_bridge.py spawns subprocess for npx remotion render and checks output duration using ffprobe
- Post (05-01): post_processor.py executes ffmpeg subprocess to copy streams while stripping metadata and adding faststart
- Post (05-01): verify_metadata_stripped() uses ffprobe JSON parser to verify container tags are empty
- Seam fix (06): _run_tts_with_retry now honors backend_url — POSTs to Colab /synthesize when set, local run_vibevoice otherwise (INFRA-01 was silently bypassed)
- Seam fix (06): orchestrator calls normalize() before TTS/align — spoken text feeds both, word_map stored in timeline meta.wordMap (AUDIO-04 was never wired in)
- Seam fix (06): storyboard_pipeline receives the timeline DICT (was passed a str path → TypeError on every run)
- Seam fix (04): render_bridge wraps props as {"timeline": ...} (--props merges flat; calculateMetadata reads props.timeline) and copies narration into video/public/ (staticFile can't reach temp dirs)
- Seam fix (04): npx.cmd on Windows; durationInFrames uses Math.ceil per VIDEO-03 (was Math.round)
- Model (v1.1): VIBEVOICE_MODEL env selects 0.5B (streaming, .pt voices) / 1.5B (voice cloning from WAV, free T4) / Large ("7B", needs Colab Pro A100-L4). 1.5B+ requires vibevoice-community fork; notebook clones the right repo per choice
- Voice (v1.1): energetic voice = clone from an energetic reference clip via 1.5B (Clone Voice tab); .pt voices auto-map to sibling demo WAV when a non-streaming model is active
- Storyboard (v1.1): LLMSceneItem gained title/bullets/emoji + big-number/comparison types — all defaulted so old outputs and the bullet fallback still validate
- Video (v1.1): SceneRenderer rebuilt as per-scene Sequences with spring entrances, staggered bullet reveals, 5 templates; CaptionRenderer rebuilt as TikTok-style pages (≤4 words/1.2s) with stroke text + active-word pop; scenes keep 220px clear of captions
- Tier1 (v1.2): 4 new scene types — chart (animated bars), steps (numbered flow), formula (KaTeX, try/catch → plain text on bad LaTeX), diagram (real labeled diagrams from Wikimedia Commons w/ license credit; every failure downgrades the scene, never crashes)
- Tier1 (v1.2): subject/grade audience control — Auto-detect default (LLM infers from script), manual dropdowns in UI; plumbed app.py → orchestrator → storyboard prompt
- Tier1 (v1.2): NO AI-generated diagrams — correctness is the product for board-exam content; Commons only
- Tier1 (v1.2): schema downgrade validators — malformed chart (<2 points), steps (<2 stages), empty formula degrade to 'bullet' inside Pydantic, so repair/fallback path stays intact

### Pending Todos

None yet.

### Blockers/Concerns

- Colab GPU URL is ephemeral (~90-min idle timeout); Phase 1 HTTP contract must handle URL churn transparently
- **ACTIVE GATE:** Phase 2 code complete — isolation_test.py must pass on Colab GPU before Phase 4 begins. Run: `python align/isolation_test.py` with TEST_CLIP_PATH set and GPU available. Gate clears when output prints "PHASE 2 ISOLATION GATE: PASSED".

## Session Continuity

Last session: 2026-07-09
Stopped at: Post-Antigravity integration review — 5 seam bugs fixed in orchestration/, render/, video/; tests updated to write real timeline fixtures instead of mocking past the seams
Resume file: None
