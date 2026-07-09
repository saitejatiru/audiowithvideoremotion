---
phase: 02-alignment-engine
plan: "02"
subsystem: align
tags: [forced-alignment, whisperx, timeline, schema, ALIGN-01, ALIGN-03]
dependency_graph:
  requires: [02-01, tts/schema.py]
  provides: [align/aligner.py, align/schema.py]
  affects: [02-03, 02-04]
tech_stack:
  added: []
  patterns: [guarded-import, pydantic-reuse, librosa-header-read]
key_files:
  created:
    - align/aligner.py
    - align/schema.py
  modified: []
decisions:
  - "whisperx import guarded inside function body — align.aligner imports cleanly on Windows without whisperx/GPU"
  - "build_timeline() uses tts.schema Pydantic models (Timeline, TimelineAudio, etc.) then returns model_dump() — no forked schema"
  - "durationSec from librosa.get_duration(path=wav_path) — enforces Pitfall 5 guard in code, not docs"
  - "soundfile.info() for sampleRate — fast header-only read, avoids double-loading full audio"
  - "wer field (not werScore) — matches TimelineMeta.wer in tts.schema"
metrics:
  duration: "5 min"
  completed: "2026-07-09"
  tasks_completed: 2
  files_created: 2
---

# Phase 2 Plan 2: WhisperX Aligner + Timeline Builder Summary

WhisperX forced-alignment path (ALIGN-01) and timeline.json builder (ALIGN-03) — schema tests GREEN on Windows, aligner tests skip cleanly without GPU; tts.schema Pydantic models reused, no fork.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | align/aligner.py — WhisperX forced alignment (ALIGN-01) | bd836c7 | align/aligner.py |
| 2 | align/schema.py — timeline.json builder (ALIGN-03) | 85ed52d | align/schema.py |

## Verification Results

```
pytest align/tests/test_schema.py align/tests/test_aligner.py -v
3 skipped, 3 xpassed in 7.22s
```

- 3 xpassed: schema tests (xfail + now PASS — strict=False, suite stays green)
- 3 skipped: aligner tests (TEST_CLIP_PATH not set — correct on Windows, no GPU)

Anti-pattern checks:
- `grep whisperx.transcribe align/aligner.py` → CLEAN (never calls transcribe)
- `grep get_duration align/schema.py` → line 78: `librosa.get_duration(path=wav_path)` (Pitfall 5 guard)
- `from align.aligner import align_known_transcript` → no ImportError on Windows
- `from align.schema import build_timeline, split_sentences` → no ImportError

## Decisions Made

- **whisperx guarded import:** `import whisperx` moved inside `align_known_transcript()` and `_load_align_model()` — module-level guard means `from align.aligner import align_known_transcript` succeeds on Windows without whisperx installed. Fails fast with clear ImportError when called without whisperx.
- **tts.schema reuse:** `build_timeline()` constructs `Timeline(...)` from tts.schema then returns `.model_dump()`. This validates inputs via Pydantic before serializing and eliminates schema drift risk (I-02).
- **librosa for durationSec, soundfile for sampleRate:** librosa.get_duration reads only the file header efficiently; soundfile.info also header-only. Both avoid full audio decode in the schema builder.
- **words[-1].end not used for durationSec:** The docstring explicitly says "ALWAYS comes from librosa.get_duration(path=)" and the test confirms: synthetic WAV is 2.0s, SAMPLE_WORDS end at 1.5s — test asserts durationSec > last word end.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- align/aligner.py: FOUND
- align/schema.py: FOUND
- Commit bd836c7 (aligner.py): FOUND
- Commit 85ed52d (schema.py): FOUND
- pytest: 3 xpassed (schema), 3 skipped (aligner) — expected
