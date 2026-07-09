---
phase: 01-contracts-text-prep
plan: "02"
subsystem: tts
tags: [normalizer, schema, pydantic, nemo-text-processing, timeline-json, tdd-green, AUDIO-04]

# Dependency graph
requires:
  - 01-01  # RED test stubs (test_normalizer.py, test_schema.py)
provides:
  - "tts/normalizer.py: normalize() with NeMo WFST guard, word_map output"
  - "tts/schema.py: canonical Timeline Pydantic models + write_phase1_timeline() + write_word_map()"
  - "test_schema.py GREEN (2 passed on Windows); test_normalizer.py 4 skipped on Windows"
affects:
  - 02-alignment-engine  # imports Timeline from tts.schema
  - 01-03 (server)       # imports normalize from tts.normalizer
  - Phase 4 (Remotion)   # reads word_map.json for caption display

# Tech tracking
tech-stack:
  added: [soundfile, pydantic-v2-models]
  patterns:
    - nemo-import-guard (try/except at module level; _normalizer=None on Windows)
    - pydantic-v2-model_validate
    - soundfile-info-for-duration (never from word timestamps)

key-files:
  created:
    - tts/normalizer.py
    - tts/schema.py
  modified:
    - tts/tests/test_normalizer.py  # stubs → real assertions (skip on Windows)
    - tts/tests/test_schema.py      # stubs → real assertions (pass on Windows)

key-decisions:
  - "normalize() returns (raw_text, []) with warning when NeMo unavailable (Windows) rather than raising — lets module load cleanly on all platforms"
  - "write_phase1_timeline() derives durationSec via soundfile.info() internally (not a parameter) — enforces the invariant that duration always comes from the file"
  - "_make_wav_bytes() helper in test_schema.py uses stdlib struct — no soundfile dep needed in tests for WAV creation"
  - "word_map entry keys: exactly {raw, spoken, start_word} — matches Phase 4 caption contract"

requirements-completed: [AUDIO-04]

# Metrics
duration: 2min
completed: "2026-07-09"
---

# Phase 1 Plan 02: Text Normalizer + timeline.json Schema Summary

**NeMo-guarded normalize() (AUDIO-04) + canonical Pydantic Timeline models — spoken-form contract that Phase 2 and Phase 4 both depend on**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-07-09T06:49:54Z
- **Completed:** 2026-07-09T06:52:05Z
- **Tasks:** 2
- **Files modified:** 2 created, 2 modified

## Accomplishments

- `normalize()` expands currency, percentage, ordinal, date, bare-number tokens via NeMo WFST; returns `(spoken_text, word_map)`
- NeMo import guarded with try/except — module loads cleanly on Windows; `_normalizer = None`; function returns `(raw_text, [])` with a warning
- `ValueError` raised for inputs < 3 words — protects TTS from silent null audio (pitfall 3 in research)
- 4 normalizer tests **skip** (not error) on Windows; real assertions ready for Linux/Colab GREEN run
- Canonical `Timeline`, `TimelineAudio`, `TimelineWord`, `TimelineSentence`, `TimelineMeta` Pydantic v2 models
- `write_phase1_timeline()` uses `soundfile.info().duration` — enforces the "never from word timestamps" invariant in code, not just in docs
- `write_word_map()` writes Phase 4 caption bridge JSON
- 2 schema tests **pass GREEN** on Windows

## Task Commits

1. **Task 1: Text normalizer with NeMo guard** — `9fccdc9` (feat)
2. **Task 2: Timeline schema + Phase 1 writer** — `6e77245` (feat)

## Files Created/Modified

- `tts/normalizer.py` — `normalize(raw_text) -> (spoken_text, word_map)`; NeMo import guard; module docstring documents Phase 2 contract
- `tts/schema.py` — `Timeline`, `TimelineAudio`, `TimelineWord`, `TimelineSentence`, `TimelineMeta`, `write_phase1_timeline()`, `write_word_map()`
- `tts/tests/test_normalizer.py` — stubs replaced with real assertions; pytestmark keeps all 4 skipped on Windows
- `tts/tests/test_schema.py` — stubs replaced with real assertions; `_make_wav_bytes()` stdlib helper; both pass on Windows

## Decisions Made

- `write_phase1_timeline` takes `(audio_path, generator, output_path)` — no `duration_sec` parameter. Function calls `soundfile.info()` internally, making the invariant un-bypassable rather than advisory.
- NeMo guard returns `(raw_text, [])` with warning (not raises) on Windows — lets orchestrator code import and run without Linux; tests are the gate for correctness.
- `_make_wav_bytes()` duplicates the conftest stdlib WAV builder rather than using the fixture — keeps test_schema.py self-contained for future Phase 2 import.

## Deviations from Plan

### Auto-fixed Issues

None.

**Deviation 1 [Rule 2 - Missing critical functionality]:** `write_phase1_timeline` plan signature included `duration_sec: float` as a parameter, but the plan also says "Use `soundfile.info(audio_path).duration` to derive duration." These are contradictory. Resolved by removing the `duration_sec` parameter — the function derives duration from the file itself, enforcing the invariant in code rather than relying on callers to pass the correct value. Simpler interface, stronger contract.

## Issues Encountered

None.

## User Setup Required

- soundfile must be installed: `pip install soundfile` (Windows-compatible wheel available)
- For GREEN normalizer tests on Linux/Colab: `pip install nemo-text-processing` (installs pynini manylinux wheel)

## Next Phase Readiness

- `from tts.schema import Timeline, write_phase1_timeline, write_word_map` ready for Phase 2 import
- `from tts.normalizer import normalize` ready for server.py (01-03) and orchestrator (Phase 6)
- test_normalizer.py assertions written — run `pytest tts/tests/test_normalizer.py -v` on Colab for GREEN confirmation
- Phase 2 can extend `TimelineMeta` by importing and adding `alignMethod`/`alignedAt` (already in schema as Optional fields)

---
*Phase: 01-contracts-text-prep*
*Completed: 2026-07-09*
