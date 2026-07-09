---
phase: 02-alignment-engine
plan: "04"
subsystem: align
tags: [pipeline, orchestration, fallback-escalation, isolation-test, ALIGN-01, ALIGN-02, ALIGN-03, ALIGN-04]
dependency_graph:
  requires: [02-02, 02-03, tts/schema.py]
  provides: [align/align_pipeline.py, align/isolation_test.py]
  affects: [phase-04-remotion-render]
tech_stack:
  added: []
  patterns: [guarded-import, lazy-escalation, monkeypatch-mock, nan-ratio-guard]
key_files:
  created:
    - align/align_pipeline.py
    - align/tests/test_pipeline.py
    - align/isolation_test.py
  modified: []
decisions:
  - "AlignmentDriftError raised (not silent fallback) on WER > threshold — Phase 6 orchestrator catches and retries TTS once, then calls use_fallback=True"
  - "NaN ratio check runs before WER to avoid wasted Whisper model inference on structurally broken alignment"
  - "_run_fallback_path sets wer_score=0.0 to signal WER was not computed, not that it passed"
  - "Pipeline unit tests fully mocked — no GPU required on Windows dev machine"
  - "Isolation scripts require GPU + TEST_CLIP_PATH; implemented as runnable Colab scripts"
  - "Phase 4 BLOCKED — isolation scripts must pass on Colab GPU first"
metrics:
  duration: "3 min"
  completed: "2026-07-09"
  tasks_completed: 2
  files_created: 3
---

# Phase 2 Plan 4: Pipeline Integration + Isolation Verification Gate Summary

`run_alignment()` single-entry orchestrator wiring aligner → NaN guard → WER guard → schema → write, with `AlignmentDriftError` for Phase 6 retry loop; pipeline unit tests GREEN on Windows (5 passed, all mocked); isolation gate scripts implemented for Colab — Phase 4 BLOCKED until Colab GPU run passes.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | align/align_pipeline.py — orchestrator with fallback escalation | 8549c15 | align/align_pipeline.py |
| 2 | Pipeline unit tests + Colab isolation scripts | c4b7146 | align/tests/test_pipeline.py, align/isolation_test.py |

## Verification Results

### pytest align/tests/ -v --tb=short (Windows, no GPU)

```
align/tests/test_aligner.py::test_words_have_timestamps             SKIPPED
align/tests/test_aligner.py::test_word_timestamps_monotonic         SKIPPED
align/tests/test_aligner.py::test_fallback_schema_matches_primary   SKIPPED
align/tests/test_pipeline.py::test_forced_ok_returns_whisperx_timeline       PASSED
align/tests/test_pipeline.py::test_drift_raises_alignment_drift_error        PASSED
align/tests/test_pipeline.py::test_structural_failure_triggers_fallback      PASSED
align/tests/test_pipeline.py::test_use_fallback_bypasses_primary_alignment   PASSED
align/tests/test_pipeline.py::test_alignment_drift_error_carries_wer_score   PASSED
align/tests/test_schema.py::test_timeline_schema_valid              XPASS
align/tests/test_schema.py::test_word_range_covers_all              XPASS
align/tests/test_schema.py::test_duration_from_audio_not_words      XPASS
align/tests/test_verifier.py::test_wer_known_good                   SKIPPED
align/tests/test_verifier.py::test_wer_drift_detected               SKIPPED
align/tests/test_verifier.py::test_check_wer_returns_tuple          SKIPPED

5 passed, 6 skipped, 3 xpassed in 3.08s
```

Zero FAILED, zero ERROR. All 5 new pipeline tests PASSED (mocked).
The 6 SKIPPED are GPU/TEST_CLIP_PATH tests — expected on Windows.

### Anti-pattern checks

- `grep whisperx.transcribe align/*.py` → CLEAN (never calls transcribe)
- `grep 'words\[-1\]\["end"\]' align/schema.py` → CLEAN (durationSec from librosa)
- `grep -c "_normalizer(" align/verifier.py` → 2 (both sides normalized)
- `WER_THRESHOLD=0.10 python -c "import align.verifier; print(align.verifier.WER_THRESHOLD)"` → 0.1
- `from align.align_pipeline import run_alignment, AlignmentDriftError` → no ImportError

### All public APIs import cleanly

```
from align.aligner        import align_known_transcript
from align.schema         import build_timeline, write_timeline, split_sentences
from align.verifier       import compute_wer, check_wer
from align.fallback       import fallback_align, nan_ratio
from align.align_pipeline import run_alignment, AlignmentDriftError
→ All public APIs import cleanly
```

## Isolation Gate Status

**Phase 4 BLOCKED — isolation scripts must pass on Colab GPU first.**

The isolation gate scripts have been implemented at `align/isolation_test.py` and are ready to run.
They have NOT been executed on Windows because whisperx + whisper_timestamped require CUDA.

### Colab Commands (exact, copy-paste)

```bash
# 1. Install dependencies (skip if already installed in Colab session)
!pip install whisperx jiwer whisper-normalizer whisper-timestamped librosa soundfile pydantic

# 2. Set the test clip path (update to your actual clip file)
import os
os.environ["TEST_CLIP_PATH"] = "/path/to/your/5-30s-english-clip.wav"
# The clip content should match SPOKEN_TEXT in isolation_test.py;
# update that variable at the top of the file if your clip uses different words.

# 3. Run the isolation gate
!python align/isolation_test.py
```

### Expected Output on Colab (passing run)

```
============================================================
ISOLATION TEST 1: KNOWN-GOOD CLIP (primary path)
============================================================
WER:          0.0xxx
alignMethod:  whisperx-forced
durationSec:  X.X
Word count:   N
Sentence cnt: M
First 3 words:
  {'w': '...', 'start': 0.xxx, 'end': 0.xxx, 'speaker': 1}
  ...
KNOWN-GOOD: PASS

============================================================
ISOLATION TEST 2: FALLBACK PATH (whisper-timestamped)
============================================================
alignMethod:  whisper-timestamped-fallback
Word count:   N
First 3 words:
  ...
FALLBACK: PASS

============================================================
PHASE 2 ISOLATION GATE: PASSED
Known-good WER:  0.0xxx (threshold 0.08)
Fallback method: whisper-timestamped-fallback
Outputs written: /tmp/timeline_known_good.json, /tmp/timeline_fallback.json
Phase 4 may begin.
============================================================
```

### Gate Decision

- If the Colab run prints "PHASE 2 ISOLATION GATE: PASSED" → **Phase 4 may begin**
- If AlignmentDriftError is raised on the known-good clip → update SPOKEN_TEXT to match clip content
- If WER > 0.08 on a correct transcript → consider `wer_model_size="large-v2"` (Pitfall 6: Indian accent ~+5-10% WER with base model)

## Decisions Made

- **AlignmentDriftError as escalation signal:** Decided against silent fallback on WER drift. The Phase 6 orchestrator must explicitly decide to retry TTS vs. use fallback — the pipeline cannot make that business decision.
- **NaN-first guard:** NaN ratio check precedes WER check. WhisperX structural failures (vocabulary mismatch on rare words) return mostly NaN timestamps; running Whisper ASR on such output wastes 10-30s of model inference.
- **wer_score=0.0 on fallback:** Sets `meta.wer = 0.0` to signal "not computed", matching TimelineMeta.wer Optional[float] contract. Phase 6 must not interpret this as "WER passed".
- **Unit tests fully mocked:** All four heavy module calls patched with `unittest.mock.patch`. Tests verify routing logic, not model accuracy — the isolation script handles real-clip accuracy verification on Colab.

## Deviations from Plan

### Auto-added: test_pipeline.py (Rule 2 — missing critical functionality)

- **Found during:** Task 2
- **Issue:** Plan Task 2 specified running isolation tests but the environment notes required unit tests with mocked heavy calls for Windows. No test file for align_pipeline.py existed.
- **Fix:** Created `align/tests/test_pipeline.py` with 5 mocked tests covering all orchestration routes.
- **Files modified:** align/tests/test_pipeline.py (new)
- **Commit:** c4b7146

## Self-Check: PASSED

- align/align_pipeline.py: FOUND
- align/tests/test_pipeline.py: FOUND
- align/isolation_test.py: FOUND
- Commit 8549c15 (align_pipeline.py): FOUND
- Commit c4b7146 (test_pipeline.py + isolation_test.py): FOUND
- pytest: 5 passed, 6 skipped, 3 xpassed, 0 failed, 0 errors — PASS
- All public APIs import cleanly — PASS
- Phase 4 gate: BLOCKED (Colab run pending — documented honestly)
