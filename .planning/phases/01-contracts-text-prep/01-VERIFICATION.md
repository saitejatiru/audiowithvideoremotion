---
phase: 01-contracts-text-prep
verified: 2026-07-09T00:00:00Z
status: human_needed
score: 5/5 must-haves verified (automated); 3 GPU/Linux behaviors require Colab
re_verification: false
human_verification:
  - test: "On Colab (Linux+GPU): from tts.normalizer import normalize; spoken, wm = normalize('I owe $42.50 today'); assert '$' not in spoken and any(e['raw']=='$42.50' for e in wm)"
    expected: "4 normalizer tests pass GREEN — currency, percentage, short-input-rejection, no-digits-in-spoken"
    why_human: "nemo-text-processing/pynini has no Windows wheel; NeMo normalizer can only run on Linux"
  - test: "On Colab: from tts.colab_launch import launch; url = launch() — inspect printed output"
    expected: "Prints 'ENDPOINT_URL = https://xxx.trycloudflare.com'; curl POST to that URL with valid Bearer token and 3+ word text returns a non-empty audio/wav file"
    why_human: "Requires real Colab environment with cloudflared installed and a live internet connection; GPU not strictly needed (dev-secret works)"
  - test: "On Colab (GPU): run two back-to-back POST /synthesize calls with speaker_id='default' and compare audio output is non-silent and consistent"
    expected: "Both calls produce WAV audio voiced by in-Samuel_man (Indian male); no re-upload needed between calls; voice_store._registry['default'] resolves to in-Samuel_man.pt"
    why_human: "Actual VibeVoice 0.5B model inference requires GPU; run_vibevoice() is mocked in all unit tests"
---

# Phase 1: Contracts & Text Prep — Verification Report

**Phase Goal:** TTS produces narration audio from a normalized script via a stable GPU HTTP endpoint; the default Indian voice is persisted and reusable across sessions; the timeline.json schema is documented as the canonical inter-stage contract.
**Verified:** 2026-07-09
**Status:** human_needed — all automated checks pass; 3 behaviors require Colab/GPU/Linux execution
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User POSTs script to GPU HTTP endpoint and receives WAV; backend swap = one env var change | VERIFIED | `test_synthesize_returns_wav` passes; `colab_launch.py` docstring documents Modal/RunPod swap; server contract is env-var-driven (`API_SECRET`, port only) |
| 2 | User can choose from available voices including at least one Indian voice | VERIFIED | `test_voices_includes_indian` passes; `in-Samuel_man.pt` exists on disk; `list_voice_ids()` returns it as "in-Samuel_man" plus "default" maps to it |
| 3 | User clones a voice from a reference clip; cloned Indian voice saved as default for subsequent generations | VERIFIED (with documented limitation) | `test_clone_voice_registered` passes; POST /clone stores and registers; default = `in-Samuel_man.pt` (0.5B limitation documented via ponytail comment; accepted per environment notes) |
| 4 | Numbers/symbols/short inputs expanded or rejected; raw→spoken word_map preserved | VERIFIED (code) / HUMAN for NeMo runtime | `normalizer.py` fully implemented; short-input rejection tested GREEN; word_map structure tested GREEN; NeMo expansion path requires Colab |
| 5 | Two back-to-back generations use same persisted default voice without manual selection | VERIFIED (mechanism) / HUMAN for audio output | `_registry` dict built at import; `get_voice_path("default")` returns `in-Samuel_man.pt` deterministically; `test_default_indian_voice_exists` passes |

**Score:** 5/5 truths mechanistically verified. 3 runtime behaviors (NeMo expansion, cloudflared tunnel, real GPU synthesis) require Colab.

---

### Required Artifacts

| Artifact | Provides | Exists | Substantive | Wired | Status |
|----------|----------|--------|-------------|-------|--------|
| `tts/tests/conftest.py` | mock_vibevoice, sample_wav_bytes, auth fixtures | Yes | Yes — real WAV builder, numpy mock | Yes — used by all test files | VERIFIED |
| `tts/tests/test_server.py` | INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03 tests | Yes | Yes — 5 real assertions | Yes — imports tts.server.app | VERIFIED |
| `tts/tests/test_normalizer.py` | AUDIO-04 tests with Windows skip guard | Yes | Yes — 4 substantive tests + pytestmark | Yes — imports tts.normalizer.normalize | VERIFIED |
| `tts/tests/test_voice_store.py` | AUDIO-05 tests | Yes | Yes — 3 real assertions including disk check | Yes — imports tts.voice_store | VERIFIED |
| `tts/tests/test_schema.py` | timeline.json contract tests | Yes | Yes — 2 tests including JSON round-trip | Yes — imports tts.schema | VERIFIED |
| `tts/normalizer.py` | normalize() with NeMo + Windows guard | Yes | Yes — full implementation with _SPAN_RE, word_map | Yes — imported by test; spoken output fed to /synthesize and Phase 2 | VERIFIED |
| `tts/schema.py` | Pydantic Timeline models + write_phase1_timeline | Yes | Yes — 5 model classes + 2 writer functions + invariant comments | Yes — imported by test; Phase 2 imports Timeline | VERIFIED |
| `tts/voice_store.py` | get_voice_path, list_voice_ids, register_voice | Yes | Yes — scans .pt files at import, default fallback logic | Yes — imported by server.py | VERIFIED |
| `tts/server.py` | FastAPI /synthesize /voices /clone | Yes | Yes — 3 routes, auth, short-input guard, WAV encoding | Yes — imported by tests and colab_launch | VERIFIED |
| `tts/colab_launch.py` | launch() — uvicorn + cloudflared | Yes | Yes — background thread + subprocess tunnel parser | Yes — references tts.server:app | VERIFIED |
| `voices/.gitkeep` | Ensures voices/ directory survives git clone | Yes | n/a | n/a | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Detail |
|------|----|-----|--------|--------|
| `tts/server.py` | `tts/voice_store.py` | `get_voice_path(req.speaker_id)` in `run_vibevoice()` | WIRED | Line 54: `voice_path = voice_store.get_voice_path(speaker_id)` |
| `tts/server.py` | `VibeVoice/app.py` | lazy import of `_load_local`, `_processor`, `_model` inside `run_vibevoice()` | WIRED (lazy) | Lines 57–73; lazy-load means import at call time, not module load — tests safely mock before it is invoked |
| `tts/colab_launch.py` | `tts/server.py` | `uvicorn.run("tts.server:app", ...)` | WIRED | Line 28 |
| `tts/schema.py` | Phase 2 (`align/`) | `Timeline` Pydantic model importable as contract | WIRED | `from tts.schema import Timeline` is the declared Phase 2 import; model validated in test |
| `tts/tests/test_server.py` | `tts/server.py` | `from tts.server import app` inside each test | WIRED | All 5 test functions import and use the real app via TestClient |

---

### Requirements Coverage

| Requirement | Plan(s) | Description | Status | Evidence |
|-------------|---------|-------------|--------|----------|
| INFRA-01 | 01-01, 01-03 | GPU stages behind stable HTTP contract; free-tier Colab now, swappable to Modal/RunPod | SATISFIED | FastAPI server with Bearer auth; colab_launch.py with cloudflared; only ENDPOINT_URL changes on backend swap |
| AUDIO-01 | 01-01, 01-03 | User inputs script and gets VibeVoice narration audio | SATISFIED | POST /synthesize returns audio/wav; test_synthesize_returns_wav passes |
| AUDIO-02 | 01-01, 01-03 | User can select a voice including an Indian voice | SATISFIED | GET /voices returns list with "default" (in-Samuel_man.pt); test_voices_includes_indian passes |
| AUDIO-03 | 01-01, 01-03 | User can clone a voice from a short reference clip | SATISFIED (0.5B scope) | POST /clone stores reference + registers voice; accepted 0.5B limitation documented via ponytail comment per environment notes |
| AUDIO-04 | 01-01, 01-02 | Script normalized before TTS; raw→spoken word_map preserved | SATISFIED (code) / HUMAN (NeMo runtime) | normalizer.py fully implemented; short-input rejection tested; NeMo path Linux-only |
| AUDIO-05 | 01-01, 01-03 | Cloned Indian voice saved and reused as default without re-upload | SATISFIED | in-Samuel_man.pt on disk; voice_store registers "default" at import; get_voice_path("default") verified by test |

No orphaned requirements. All 6 phase-1 IDs are claimed by plans and verified above.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `tts/server.py` line 1 | `ponytail: AUDIO-03 via 0.5B stores reference audio only...` | Info | Intentional documented limitation per accepted design; not a gap |
| `tts/normalizer.py` line 62 | `return raw_text, []` when `_normalizer is None` | Info | Correct graceful fallback for Windows dev; NeMo unavailable = warning + no-op, tests skip |
| `tts/server.py` line 44 | `run_vibevoice` uses `import copy/torch/numpy` inside function body | Info | Lazy GPU import pattern — deliberate; lets server import and TestClient work without GPU or vibevoice installed |

No blockers or warnings. All three patterns are intentional and documented.

---

### Human Verification Required

#### 1. NeMo text normalization (AUDIO-04 runtime)

**Test:** On a Colab (Linux) cell after `pip install nemo-text-processing`:
```python
from tts.normalizer import normalize
spoken, wm = normalize("I owe $42.50 today")
print(spoken, wm)
spoken2, _ = normalize("The value is 25% complete today")
print(spoken2)
```
**Expected:** `spoken` contains no `$` or bare `42.50`; `wm[0]["raw"] == "$42.50"`; `spoken2` contains no bare digit tokens; `pytest tts/tests/test_normalizer.py` shows 4 PASSED (not 4 SKIPPED).
**Why human:** `pynini` has no Windows wheel; `_normalizer` is `None` on this machine so the NeMo code path cannot execute here.

#### 2. Cloudflared tunnel + live /synthesize (INFRA-01 runtime)

**Test:** On Colab after `git clone` and `pip install fastapi uvicorn soundfile`:
```python
from tts.colab_launch import launch
url = launch()  # should print ENDPOINT_URL = https://xxx.trycloudflare.com
```
Then from another cell or local terminal:
```bash
curl -s -H "Authorization: Bearer dev-secret" \
  -X POST $url/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world this is a test"}' -o out.wav
ls -lh out.wav  # must be > 0 bytes
```
**Expected:** `launch()` prints a `trycloudflare.com` URL; `out.wav` is a non-empty WAV (GPU required for non-silence audio; CPU fallback via `_generate_cpu` is also acceptable for smoke test).
**Why human:** Requires live Colab + cloudflared binary + internet; cannot test tunneling locally.

#### 3. Real GPU synthesis with default Indian voice (AUDIO-01, AUDIO-05)

**Test:** On Colab with GPU runtime: run two consecutive synthesize calls without any voice re-upload.
```python
import requests, os
h = {"Authorization": "Bearer dev-secret"}
r1 = requests.post("http://localhost:8000/synthesize", json={"text":"The quick brown fox jumped over the lazy dog"}, headers=h)
r2 = requests.post("http://localhost:8000/synthesize", json={"text":"Numbers and percentages are expanded before synthesis"}, headers=h)
assert r1.status_code == r2.status_code == 200
assert len(r1.content) > 0 and len(r2.content) > 0
```
**Expected:** Both return 200 audio/wav with non-empty content; audio audibly sounds like the Samuel Indian voice; no manual voice selection or re-upload between calls.
**Why human:** VibeVoice 0.5B inference requires GPU; `run_vibevoice` is mocked in all unit tests; real audio quality can only be assessed by listening.

---

## Gaps Summary

No gaps. All artifacts exist, are substantive, and are wired correctly. The three human verification items are expected platform constraints (Windows dev machine cannot run NeMo or cloudflared against a real GPU), not implementation defects. The AUDIO-03 0.5B limitation is explicitly documented and accepted per the environment notes.

---

_Verified: 2026-07-09_
_Verifier: Claude (gsd-verifier)_
