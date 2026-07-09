# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-08)

**Core value:** Narration, on-screen visuals, and captions are perfectly synced to the audio.
**Current focus:** Phase 2 — Alignment Engine

## Current Position

Phase: 2 of 6 (Alignment Engine)
Plan: 3 of 3 in current phase
Status: In progress
Last activity: 2026-07-09 — Plan 02-03 complete: ASR-WER verifier + whisper-timestamped fallback (ALIGN-02, ALIGN-04)

Progress: [██████░░░░] ~33%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 3 min
- Total execution time: 0.23 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-contracts-text-prep | 3 | 9 min | 3 min |
| 02-alignment-engine | 3 | 10 min | 3.3 min |

**Recent Trend:**
- Last 5 plans: 2 min, 4 min, 2 min, 3 min, 3 min
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

### Pending Todos

None yet.

### Blockers/Concerns

- Colab GPU URL is ephemeral (~90-min idle timeout); Phase 1 HTTP contract must handle URL churn transparently
- Phase 2 (alignment) is the critical path — do not start Phase 4 (Remotion render) until Phase 2 is verified with a real clip and WER is at acceptable levels

## Session Continuity

Last session: 2026-07-09
Stopped at: Completed 02-03-PLAN.md — ASR-WER verifier + fallback committed (74213fb, df99a71)
Resume file: None
