---
phase: 01-contracts-text-prep
plan: "01"
subsystem: testing
tags: [pytest, tdd, red-state, tts, normalizer, voice-store, schema, httpx]

# Dependency graph
requires: []
provides:
  - "14 RED test stubs across 4 test files covering INFRA-01, AUDIO-01..05"
  - "conftest.py with mock_vibevoice, sample_wav_bytes (stdlib WAV), auth fixtures"
  - "inter-phase timeline.json contract defined in test_schema.py"
  - "tts/ and tts/tests/ Python packages initialized"
affects:
  - 01-contracts-text-prep/wave-2-plans
  - 02-alignment-engine

# Tech tracking
tech-stack:
  added: [pytest, stdlib-struct-wav-builder]
  patterns: [deferred-imports-in-test-bodies, pytestmark-skipif-platform, red-green-tdd]

key-files:
  created:
    - tts/__init__.py
    - tts/tests/__init__.py
    - tts/tests/conftest.py
    - tts/tests/test_server.py
    - tts/tests/test_normalizer.py
    - tts/tests/test_voice_store.py
    - tts/tests/test_schema.py
  modified: []

key-decisions:
  - "Deferred imports inside test bodies so all 14 tests collect on Windows without ImportError at collection time"
  - "stdlib struct used to build sample WAV bytes — no soundfile dep needed in RED state"
  - "pytestmark skipif(Windows) on test_normalizer.py so normalizer tests are collected+skipped on Windows, not erroring"

patterns-established:
  - "TDD RED pattern: from tts.X import Y inside test body; pytest.fail('not implemented') body; test fails cleanly"
  - "Platform guard pattern: pytestmark = pytest.mark.skipif(platform.system() == 'Windows', reason=...) for Linux-only deps"

requirements-completed: [INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-04, AUDIO-05]

# Metrics
duration: 4min
completed: "2026-07-09"
---

# Phase 1 Plan 01: TDD Test Scaffolding Summary

**14 RED pytest stubs across 4 modules (server, normalizer, voice_store, schema) defining the full Phase 1 contract for INFRA-01 and AUDIO-01..05**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-09T06:44:04Z
- **Completed:** 2026-07-09T06:48:00Z
- **Tasks:** 1 (single TDD RED task)
- **Files modified:** 7 created, 0 modified

## Accomplishments
- 14 test stubs collected cleanly by pytest on Windows (zero collection errors)
- normalizer tests correctly skipped on Windows via pytestmark (not errored) — pynini has no Windows wheel
- sample_wav_bytes fixture built with stdlib struct, no soundfile dependency in RED state
- inter-phase timeline.json contract captured in test_schema.py for Phase 2 alignment engine

## Task Commits

1. **Task 1: RED test stubs for INFRA-01, AUDIO-01..05** - `af6c262` (test)

## Files Created/Modified
- `tts/__init__.py` - empty package marker
- `tts/tests/__init__.py` - empty package marker
- `tts/tests/conftest.py` - shared fixtures: mock_vibevoice, sample_wav_bytes, test_secret, auth_headers, set_api_secret
- `tts/tests/test_server.py` - 5 stubs: synthesize 200+WAV, 401 bad token, 400 short input, /voices Indian, /clone registration
- `tts/tests/test_normalizer.py` - 4 stubs (Windows skipped): currency expand, short reject, word_map keys, no bare digits
- `tts/tests/test_voice_store.py` - 3 stubs: default path exists, list nonempty, includes default/samuel
- `tts/tests/test_schema.py` - 2 stubs: Timeline.model_validate, write_phase1_timeline structure

## Decisions Made
- Deferred module imports into test function bodies (not module-level) so `pytest --collect-only` lists all 14 tests on Windows without collection errors. Module-level imports from non-existent tts.server etc. would cause ImportError at collection time.
- Built WAV bytes with stdlib `struct` rather than adding soundfile as a dev dependency in RED state — soundfile can be added when GREEN implementation needs it.
- pytestmark skipif(Windows) on test_normalizer.py is correct: tests are collected and skipped, not errored — this is the behavior Wave 2 needs to verify GREEN on Linux.

## Deviations from Plan

None - plan executed exactly as written. The deferred-import pattern was chosen to satisfy the `--collect-only` success criterion on Windows.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All test contracts defined. Wave 2 plans can implement tts/server.py, tts/normalizer.py, tts/voice_store.py, tts/schema.py and run `pytest tts/tests/ -x -q` to verify GREEN.
- test_synthesize_returns_wav will need mock_vibevoice fixture wired to the real app client (httpx TestClient) — Wave 2 task.
- normalizer tests require Linux; run in Colab or Docker for GREEN verification.

---
*Phase: 01-contracts-text-prep*
*Completed: 2026-07-09*
