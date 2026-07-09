---
phase: 01-contracts-text-prep
plan: "03"
subsystem: tts
tags: [fastapi, voice-store, tts-server, colab, cloudflared, tdd-green, INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-05]

# Dependency graph
requires:
  - 01-01  # test stubs (test_server.py, test_voice_store.py)
  - 01-02  # normalizer.py, schema.py
provides:
  - "tts/voice_store.py: get_voice_path, list_voice_ids, register_voice"
  - "tts/server.py: FastAPI app with POST /synthesize, GET /voices, POST /clone"
  - "tts/colab_launch.py: launch() starts uvicorn + cloudflared, returns ENDPOINT_URL"
  - "voices/.gitkeep: voices/ directory present after git clone"
  - "test_server.py GREEN (5 passed); test_voice_store.py GREEN (3 passed)"
affects:
  - 02-alignment-engine  # calls POST /synthesize
  - Phase 6 orchestrator # uses ENDPOINT_URL / HTTP contract

# Tech tracking
tech-stack:
  added: [fastapi, httpx, python-multipart, soundfile]
  patterns:
    - lazy-load-model-inside-endpoint (run_vibevoice not called at import)
    - bearer-token-via-env-var (API_SECRET, dev-secret default)
    - httpbearer-depends-pattern (FastAPI HTTPBearer + Depends)
    - voice-registry-in-memory-with-disk-fallback

key-files:
  created:
    - tts/voice_store.py
    - tts/server.py
    - tts/colab_launch.py
    - voices/.gitkeep
  modified:
    - tts/tests/test_server.py   # stubs -> GREEN assertions
    - tts/tests/test_voice_store.py  # stubs -> GREEN assertions

key-decisions:
  - "run_vibevoice() lazy-loaded inside endpoint — server.py and TestClient work on Windows without GPU or vibevoice package"
  - "voice_store registry is in-memory dict built at import time; no DB needed (ponytail: global state, per-process for now)"
  - "POST /clone stubs 0.5B cloning with a warning log; stores file under voices/; ponytail comment documents 1.5B upgrade path"
  - "voices/.gitkeep ensures voices/ directory survives git clone before any .wav is committed"
  - "_check_auth reads API_SECRET at call time (not module load) so monkeypatch.setenv works in tests"

requirements-completed: [INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-05]

# Metrics
duration: 3min
completed: "2026-07-09"
---

# Phase 1 Plan 03: FastAPI Server + Voice Store + Colab Launcher Summary

**FastAPI TTS HTTP service (INFRA-01) with voice registry, 3 endpoints, and Colab cloudflared launcher — permanent HTTP contract that all GPU backends must honour**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-07-09T07:18:08Z
- **Completed:** 2026-07-09T07:20:51Z
- **Tasks:** 3
- **Files modified:** 4 created, 2 modified

## Accomplishments

- `voice_store.py`: auto-scans VibeVoice/demo/voices/streaming_model/**/*.pt at import; registers `default` -> `in-Samuel_man.pt` (AUDIO-05 fallback path with `voices/default_indian.wav` as primary); `get_voice_path`, `list_voice_ids`, `register_voice` exported
- `server.py`: FastAPI app with exactly-contracted endpoints; Bearer auth via API_SECRET env var; 3-word minimum guard on /synthesize; `run_vibevoice` lazy-loaded so Windows TestClient works without GPU; ponytail comment on AUDIO-03 0.5B limitation
- `colab_launch.py`: `launch()` starts uvicorn in daemon thread + cloudflared tunnel, returns ephemeral HTTPS URL; module docstring documents the URL churn lifecycle and Modal/RunPod upgrade path
- `voices/.gitkeep`: voices/ directory present after git clone
- test_server.py: 5 stubs -> GREEN; test_voice_store.py: 3 stubs -> GREEN
- Full suite: 10 passed, 4 skipped (normalizer tests correctly skipped on Windows)

## Task Commits

1. **Task 1: Voice store** - `4ad0e77` (feat)
2. **Task 2: FastAPI server** - `088321c` (feat)
3. **Task 3: Colab launch + voices/.gitkeep** - `daac24d` (feat)

## Files Created/Modified

- `tts/voice_store.py` — get_voice_path/list_voice_ids/register_voice; AUDIO-05 persistence comment
- `tts/server.py` — FastAPI app; POST /synthesize (auth + WAV), GET /voices, POST /clone; ponytail AUDIO-03 comment
- `tts/colab_launch.py` — launch() = uvicorn thread + cloudflared; ephemeral URL docstring
- `voices/.gitkeep` — ensures voices/ dir in git
- `tts/tests/test_server.py` — 5 stubs -> real assertions with TestClient + mock_vibevoice
- `tts/tests/test_voice_store.py` — 3 stubs -> real assertions (pure filesystem, Windows-green)

## Decisions Made

- `run_vibevoice` is a module-level function that is lazy-loaded internally — the entire VibeVoice model stack (`_load_local`, torch, vibevoice package) is never touched at import time. Tests mock it via `monkeypatch.setattr("tts.server.run_vibevoice", ...)`.
- `_check_auth` reads `os.environ.get("API_SECRET")` at call time rather than capturing the value at module load — this is the minimal change that makes `monkeypatch.setenv` work correctly in tests.
- `register_voice` copies the file to `voices/{voice_id}{ext}` on disk and updates the in-memory registry — no persistence layer needed for Phase 1.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

- `pip install fastapi uvicorn httpx python-multipart soundfile` for server.py + tests
- For Colab launch: `pip install cloudflared` (or install cloudflared binary)
- For GPU synthesis: vibevoice package + torch on Colab (lazy-loaded, not needed for tests)

## Next Phase Readiness

- Phase 1 complete: all 10 runnable tests GREEN on Windows (4 normalizer tests skip correctly)
- Phase 2 (alignment engine) can call POST /synthesize at ENDPOINT_URL after `launch()`
- Switching GPU backend: set ENDPOINT_URL env var only — /synthesize contract unchanged (INFRA-01)
- Colab verification: `from tts.colab_launch import launch; url = launch()` then curl /synthesize

## Self-Check: PASSED

- tts/voice_store.py: FOUND
- tts/server.py: FOUND
- tts/colab_launch.py: FOUND
- voices/.gitkeep: FOUND
- Commits 4ad0e77, 088321c, daac24d: FOUND in git log

---
*Phase: 01-contracts-text-prep*
*Completed: 2026-07-09*
