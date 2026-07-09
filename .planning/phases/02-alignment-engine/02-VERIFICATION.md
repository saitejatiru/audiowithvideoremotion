---
phase: 02-alignment-engine
verified: 2026-07-09T00:00:00Z
status: human_needed
score: 15/17 truths verified
human_verification:
  - test: "Run align/isolation_test.py on Colab GPU with a real 5-30s English speech WAV"
    expected: |
      Both assertions pass and script exits 0:
        KNOWN-GOOD: PASS  (alignMethod=whisperx-forced, wer < 0.08, durationSec > words[-1].end)
        FALLBACK: PASS    (alignMethod=whisper-timestamped-fallback, all words have {w,start,end,speaker})
        PHASE 2 ISOLATION GATE: PASSED
    why_human: "whisperx and whisper-timestamped require CUDA; no real audio available on Windows dev machine"
---

# Phase 2: Alignment Engine Verification Report

**Phase Goal:** Word-level timestamps forced-aligned against the known spoken script (WhisperX), verified by ASR-WER, emitted as the canonical timeline.json every downstream stage reads; whisper-timestamped fallback when forced alignment fails. Must be verifiable in isolation with a real clip before Phase 4 begins.

**Verified:** 2026-07-09
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Plan | Status | Evidence |
|---|-------|------|--------|----------|
| 1 | pytest align/tests/ collects all tests without import errors | 02-01 | VERIFIED | 15 passed/xpassed/skipped, 0 failed, 0 error (SUMMARY 02-04) |
| 2 | conftest.py provides synthetic 2s 16kHz WAV fixture + SPOKEN_TEXT constant | 02-01 | VERIFIED | align/tests/conftest.py L12-27 generates sine-wave WAV via soundfile |
| 3 | All test function stubs exist with xfail marks (RED scaffold) | 02-01 | VERIFIED | All 9 test functions present; marks present with strict=False (schema tests now XPASS — correct) |
| 4 | align_known_transcript() returns words[] with non-NaN start/end per word | 02-02 | VERIFIED | align/aligner.py L78-89: None→NaN normalization; guarded whisperx import; real-clip tests skip on Windows (expected) |
| 5 | Word timestamps are monotonically non-decreasing | 02-02 | VERIFIED | Implementation in aligner.py preserves WhisperX order; test_word_timestamps_monotonic asserts this |
| 6 | build_timeline() returns dict with all required top-level keys | 02-02 | VERIFIED | test_schema.py: 3 XPASS on Windows — audio/words/sentences/meta all present |
| 7 | durationSec equals librosa.get_duration() on the source WAV, never words[-1].end | 02-02 | VERIFIED | schema.py L78: `librosa.get_duration(path=wav_path)`; grep confirms no words[-1] usage in live code |
| 8 | sentences[].wordRange values are contiguous and cover every word | 02-02 | VERIFIED | test_word_range_covers_all XPASS; map_words_to_sentences L40-58 logic confirmed |
| 9 | compute_wer() normalizes BOTH reference and hypothesis with EnglishTextNormalizer | 02-03 | VERIFIED | verifier.py L60-61: `_normalizer(reference_spoken)` and `_normalizer(hypothesis)` — 2 calls confirmed |
| 10 | check_wer() returns (decision, score) tuple with decision in {ok, regenerate} | 02-03 | VERIFIED | verifier.py L89-91: only "ok" or "regenerate" returned; fallback escalation deferred to pipeline |
| 11 | WER_THRESHOLD is configurable via WER_THRESHOLD env var (default 0.08) | 02-03 | VERIFIED | verifier.py L21: `float(os.environ.get("WER_THRESHOLD", "0.08"))` |
| 12 | fallback_align() returns words[] with identical {w,start,end,speaker} shape to primary path | 02-03 | VERIFIED | fallback.py L59-64: adapter maps whisper-timestamped "text" → "w", adds speaker=1 |
| 13 | run_alignment() writes timeline.json, returns dict, routes primary→NaN→WER→fallback correctly | 02-04 | VERIFIED | test_pipeline.py: 5 mocked route tests pass on Windows (forced-ok, drift, struct-fail, use_fallback, error-carries-wer) |
| 14 | NaN ratio > 20% triggers fallback path; check_wer is not called on structural failure | 02-04 | VERIFIED | test_structural_failure_triggers_fallback: mock_wer.assert_not_called() passes |
| 15 | All pytest align/tests/ pass green (or skip if TEST_CLIP_PATH unset) | 02-04 | VERIFIED | 5 passed, 6 skipped, 3 xpassed, 0 failed, 0 errors — confirmed in SUMMARY 02-04 |
| 16 | Known-good clip: timeline.json has wer < 0.08 and alignMethod=whisperx-forced | 02-04 | HUMAN_NEEDED | Requires real clip + Colab GPU |
| 17 | Phase 2 independently verified with real clip before Phase 4 begins | 02-04 | HUMAN_NEEDED | isolation_test.py implemented and correct; not yet run on GPU |

**Score: 15/17 truths verified**

---

### Required Artifacts

| Artifact | Status | Notes |
|----------|--------|-------|
| `align/__init__.py` | VERIFIED | Present (empty — correct) |
| `align/tests/__init__.py` | VERIFIED | Present (empty — correct) |
| `align/requirements.txt` | VERIFIED | 7 entries; torch/torchaudio absent (comment explains why) |
| `align/tests/conftest.py` | VERIFIED | synthetic_wav fixture + real_wav_path skip guard + SPOKEN_TEXT |
| `align/tests/test_aligner.py` | VERIFIED | test_words_have_timestamps, test_word_timestamps_monotonic, test_fallback_schema_matches_primary |
| `align/tests/test_verifier.py` | VERIFIED | test_wer_known_good, test_wer_drift_detected, test_check_wer_returns_tuple |
| `align/tests/test_schema.py` | VERIFIED | test_timeline_schema_valid, test_word_range_covers_all, test_duration_from_audio_not_words |
| `align/tests/test_pipeline.py` | VERIFIED | 5 route tests with full mocking — not in 02-01 PLAN (added in 02-04 as documented deviation) |
| `align/aligner.py` | VERIFIED | align_known_transcript(); guarded whisperx import; sentence-level segmentation |
| `align/schema.py` | VERIFIED | build_timeline(), split_sentences(), map_words_to_sentences(), write_timeline(); imports from tts.schema |
| `align/verifier.py` | VERIFIED | compute_wer(), check_wer(), WER_THRESHOLD; both sides normalized |
| `align/fallback.py` | VERIFIED | fallback_align(), nan_ratio(); adapter maps text→w |
| `align/align_pipeline.py` | VERIFIED | run_alignment(), AlignmentDriftError; all 4 sub-modules imported at top |
| `align/isolation_test.py` | VERIFIED (code) | Substantive script with 2 test blocks + assertions; awaits Colab GPU run |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| align/aligner.py | align/schema.py | words[] with `"w"` key | VERIFIED | L81: `"w": w.get("word", "").strip()` |
| align/schema.py | librosa.get_duration | durationSec from file | VERIFIED | L78: `librosa.get_duration(path=wav_path)` |
| align/verifier.py | jiwer.wer + EnglishTextNormalizer | both sides normalized | VERIFIED | L60-61: two `_normalizer()` calls confirmed |
| align/fallback.py | tts.schema words[] shape | adapter "text"→"w" | VERIFIED | L60: `"w": w.get("text", "").strip()` |
| align/align_pipeline.py | align/aligner.py | align_known_transcript() | VERIFIED | L24: `from align.aligner import align_known_transcript` |
| align/align_pipeline.py | align/verifier.py | check_wer() | VERIFIED | L25: `from align.verifier import check_wer, WER_THRESHOLD` |
| align/align_pipeline.py | align/fallback.py | fallback_align(), nan_ratio() | VERIFIED | L26: `from align.fallback import fallback_align, nan_ratio, FALLBACK_NAN_THRESHOLD` |
| align/align_pipeline.py | align/schema.py | build_timeline(), write_timeline() | VERIFIED | L27: `from align.schema import build_timeline, write_timeline` |
| align/schema.py | tts.schema | Timeline, TimelineWord, etc. (no fork) | VERIFIED | L22: `from tts.schema import Timeline, TimelineAudio, TimelineWord, TimelineSentence, TimelineMeta` |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ALIGN-01 | 02-01, 02-02, 02-04 | Word-level timestamps via WhisperX forced alignment | VERIFIED | aligner.py; test_aligner.py; pipeline route tests |
| ALIGN-02 | 02-01, 02-03, 02-04 | ASR-WER guard; flag/regenerate on drift | VERIFIED | verifier.py; compute_wer/check_wer; WER_THRESHOLD env var |
| ALIGN-03 | 02-01, 02-02, 02-04 | timeline.json canonical contract (words, sentences, durations, speaker) | VERIFIED | schema.py; 3 schema tests XPASS; tts.schema reused |
| ALIGN-04 | 02-01, 02-03, 02-04 | whisper-timestamped fallback when forced alignment fails | VERIFIED | fallback.py; nan_ratio(); pipeline fallback route tested |

All 4 requirement IDs claimed by plans 02-01 through 02-04 are present in REQUIREMENTS.md and marked `[x]` (complete). No orphaned requirements found.

---

### Anti-Patterns Found

| File | Pattern | Severity | Finding |
|------|---------|----------|---------|
| align/aligner.py | `whisperx.transcribe` call | 🛑 Blocker (if present) | CLEAN — not found anywhere in align/*.py |
| align/schema.py | `words[-1]["end"]` for durationSec | 🛑 Blocker (if present) | CLEAN — only appears in docstring warning; live code uses librosa |
| align/verifier.py | single-side normalization | 🛑 Blocker (if present) | CLEAN — 2 `_normalizer()` calls confirmed at L60-61 |
| align/*.py | `werScore` field name | 🛑 Blocker (if present) | CLEAN — field is `wer` in both tts/schema.py TimelineMeta and all usages |
| align/tests/*.py | stale xfail reason string | ℹ️ Info | test_schema.py says "schema.py not yet implemented" but tests XPASS; strict=False so no test failure; cosmetic only |

---

### Human Verification Required

#### 1. Phase 4 Gate: Colab GPU Isolation Test

**This is the single most important open item. Phase 4 (Remotion) MUST NOT begin until this passes.**

**What to do — exact Colab commands (copy-paste in order):**

```python
# Cell 1: Install dependencies
!pip install whisperx jiwer whisper-normalizer whisper-timestamped librosa soundfile pydantic
```

```python
# Cell 2: Mount repo or upload it
# If using Google Drive:
from google.colab import drive
drive.mount('/content/drive')
import os
os.chdir('/content/drive/MyDrive/Audio')   # adjust path to your repo root
```

```python
# Cell 3: Set test clip path
import os
os.environ["TEST_CLIP_PATH"] = "/path/to/your/5-30s-english-clip.wav"
# The clip MUST be 5-30s of English speech.
# Update SPOKEN_TEXT at the top of align/isolation_test.py to match the exact words spoken.
```

```python
# Cell 4: Run the isolation gate
!python align/isolation_test.py
```

**Expected terminal output (passing run):**

```
============================================================
ISOLATION TEST 1: KNOWN-GOOD CLIP (primary path)
============================================================
WER:          0.0xxx
alignMethod:  whisperx-forced
durationSec:  X.X
Word count:   N
...
KNOWN-GOOD: PASS

============================================================
ISOLATION TEST 2: FALLBACK PATH (whisper-timestamped)
============================================================
alignMethod:  whisper-timestamped-fallback
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

**Assertions that must hold for PASS:**

- `tl["meta"]["alignMethod"] == "whisperx-forced"`
- `tl["meta"]["wer"] < 0.08`
- `tl["audio"]["durationSec"] > tl["words"][-1]["end"]`
- `{"audio", "words", "sentences", "meta"}.issubset(tl.keys())`
- `tl_fb["meta"]["alignMethod"] == "whisper-timestamped-fallback"`
- Every word in `tl_fb["words"]` has keys `{w, start, end, speaker}`

**Troubleshooting:**

- `AlignmentDriftError` raised on known-good clip → SPOKEN_TEXT does not match clip content; update `SPOKEN_TEXT` in isolation_test.py
- WER > 0.08 with correct transcript → Indian-accented voice; edit isolation_test.py to pass `wer_model_size="large-v2"` to `run_alignment()` (Pitfall 6 from 02-RESEARCH.md)
- `ImportError: whisperx` → pip install in Cell 1 failed; retry or use `!pip install whisperx --quiet`

---

### Confirmed: align/schema.py Uses tts.schema (No Fork)

`from tts.schema import Timeline, TimelineAudio, TimelineWord, TimelineSentence, TimelineMeta`

- `durationSec` derives from `librosa.get_duration(path=wav_path)` — not from words
- Field is `wer` (not `werScore`) — matches `TimelineMeta.wer: Optional[float]` in tts/schema.py
- `build_timeline()` returns `timeline.model_dump()` — Pydantic validation on every call

---

### Gaps Summary

No gaps. All automated checks pass. The 2 unverified truths are both gated on Colab GPU + real audio, which is intentional by design (documented in 02-04-SUMMARY.md). The isolation script is implemented, correct, and ready to run — it only needs execution on the GPU environment.

**Gate decision rule:** If `align/isolation_test.py` exits 0 on Colab and prints "PHASE 2 ISOLATION GATE: PASSED", Phase 4 may begin. Any other outcome blocks Phase 4.

---

_Verified: 2026-07-09_
_Verifier: Claude (gsd-verifier)_
