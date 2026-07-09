# Phase 1: Contracts & Text Prep — Research

**Researched:** 2026-07-09
**Domain:** TTS HTTP endpoint (VibeVoice), text normalization, voice persistence, timeline.json schema definition
**Confidence:** HIGH (stack, VibeVoice API, schema); MEDIUM (voice cloning persistence, NeMo token mapping)

---

## Summary

Phase 1 lays every foundation the rest of the pipeline depends on. It has three distinct jobs:
(1) expose VibeVoice behind a stable HTTP contract so the orchestrator can call `POST /synthesize`
identically on Colab today and Modal/RunPod later; (2) build a text normalizer that expands
numbers/dates/currency/symbols into spoken words and preserves a `raw→spoken` word map so Phase 2
can pass digits-free text to wav2vec2 alignment; and (3) persist and register a cloned Indian voice
as the default speaker so every subsequent generation reuses it without manual re-upload.

The existing `app.py` uses a Gradio proxy pattern. That is the wrong abstraction for an orchestrator
pipeline: the Gradio `/predict` API is tied to UI widget positions, breaks when components change, and
is incompatible with Modal/RunPod deployment. Replace it with a FastAPI `POST /synthesize` endpoint
on Colab, tunnelled via cloudflared (no account required, HTTPS included). That contract becomes the
permanent interface — every future backend swap is a one-line URL change.

Text normalization uses `nemo-text-processing 1.2.0`. It is the only Python library in this space with
production coverage of all required semiotic classes: cardinals, ordinals, currency, percentages,
dates, URLs/electronic, and symbols. `num2words` covers numbers only and requires hand-rolled regex
for everything else; `WeTextProcessing` is viable but less battle-tested in English. Voice cloning
from a reference clip requires the 1.5B community fork (`vibevoice-community/VibeVoice`) on Colab
GPU; the 0.5B model uses only pre-computed `.pt` cached prompts. The cloned Indian reference audio
file should be committed to the git repo so Colab always has it after a `git clone` — this is how
AUDIO-05 (persist across sessions) is solved without Google Drive.

**Primary recommendation:** FastAPI + cloudflared on Colab (1.5B community fork), `nemo-text-processing`
for normalization, reference Indian audio committed to repo as `voices/default_indian.wav`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | GPU stages run behind a stable HTTP contract — Colab now, swappable to Modal/RunPod by URL change | FastAPI `POST /synthesize` + cloudflared Quick Tunnel; identical contract on all backends; Bearer auth from Colab Secrets |
| AUDIO-01 | User can input a script and get VibeVoice narration audio back | Existing `generate()` API in `realtime_model_inference_from_file.py`; wrap in FastAPI `POST /synthesize` returning raw WAV bytes |
| AUDIO-02 | User can select a voice, including an Indian voice | `in-Samuel_man.pt` already present in `demo/voices/streaming_model/`; expose `GET /voices` listing; pass `speaker_id` in POST body |
| AUDIO-03 | User can clone a voice from a short reference clip | Requires 1.5B community fork (`vibevoice-community/VibeVoice`); upload reference audio to `demo/voices/` or send as multipart to `POST /clone`; model uses raw audio as conditioning prompt |
| AUDIO-04 | Script is normalized before synthesis, keeping a raw→spoken map for captions | `nemo-text-processing 1.2.0` Normalizer; pre-tokenize with regex to identify spans, normalize each, zip for map; reject input < 3 words |
| AUDIO-05 | Cloned Indian reference voice is saved to disk and reused as default speaker without re-upload | Commit reference audio to repo at `voices/default_indian.wav`; auto-loaded at FastAPI startup as the `default` speaker_id |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115.x | HTTP endpoint exposing `POST /synthesize` | Backend-agnostic; identical on Colab/Modal/RunPod; standard Python web framework |
| uvicorn | 0.30.x | ASGI server for FastAPI | FastAPI's documented server; single-line launch |
| nemo-text-processing | 1.2.0 | Text normalization (numbers, dates, currency, symbols → spoken words) | Only Python library covering all required semiotic classes; NVIDIA-maintained; pip-installable on Colab without C++ compilation |
| pyngrok / cloudflared | cloudflared latest | Colab-to-public HTTPS tunnel | cloudflared Quick Tunnel: no account, no limits, HTTPS auto-included; URL changes on restart but HTTP contract is stable |
| python-multipart | 0.0.9 | FastAPI file upload support for voice cloning reference clip | FastAPI dep for `UploadFile` |
| soundfile | 0.12.x | Write numpy float32 array to WAV bytes for HTTP response | Lightweight; VibeVoice already uses 24kHz numpy output |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torch | ≥2.0 + CUDA 12.8 | GPU backend for VibeVoice 1.5B | Always on Colab T4; fall back to cpu/float32 for small tests |
| pydantic | ≥2.0 | Request/response schema validation (FastAPI dep) | Always; comes with FastAPI |
| num2words | 0.5.14 | Fallback number-to-word conversion | Only if NeMo install fails; covers cardinals/ordinals but NOT currency/dates/symbols |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nemo-text-processing | WeTextProcessing 1.2.0 | Smaller install (7MB FSTs vs NeMo's 76MB), simpler install, no pynini — but English support less battle-tested and no DATE/ELECTRONIC classes verified |
| nemo-text-processing | num2words 0.5.14 + custom regex | Covers only numbers; you hand-roll currency/date/symbol parsing — re-implements what NeMo provides; skip unless NeMo install fails |
| cloudflared | pyngrok | pyngrok needs an ngrok account and authtoken; free tier has 1 agent and rate limits. cloudflared Quick Tunnel is strictly better for no-account Colab use |
| Raw FastAPI | gradio_client proxy (existing app.py) | Gradio API tied to UI widget positions; breaks on component change; incompatible with Modal/RunPod deployment |

**Installation (Colab):**
```bash
# Install cloudflared (Linux binary)
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared-linux-amd64.deb

# Install Python deps
pip install fastapi uvicorn python-multipart soundfile nemo-text-processing
# nemo-text-processing pulls pynini (manylinux wheel available for py3.9–3.14, no compilation)

# Clone community fork for 1.5B voice cloning
!git clone https://github.com/vibevoice-community/VibeVoice.git vibevoice_1p5b
%cd vibevoice_1p5b
!pip install -q -e .
```

---

## Architecture Patterns

### Recommended Project Structure

```
tts/
├── server.py           # FastAPI app: POST /synthesize, GET /voices, POST /clone
├── normalizer.py       # Text normalization + raw→spoken map (AUDIO-04)
├── voice_store.py      # Voice registry: list voices, get default, load cached prompt
├── tests/
│   ├── test_normalizer.py   # normalization + word map tests
│   └── test_server.py       # HTTP contract smoke tests (httpx TestClient)
voices/
└── default_indian.wav  # Reference audio committed to repo (AUDIO-05)
```

**Language note:** All Phase 1 code is Python. The Remotion/Node layer doesn't appear until Phase 4.

### Pattern 1: FastAPI Endpoint (INFRA-01, AUDIO-01, AUDIO-02)

**What:** Minimal HTTP server wrapping VibeVoice generate call. Returns raw WAV bytes.
**Contract is final:** this exact request/response shape is what all backends (Colab/Modal/RunPod) must implement.

```python
# tts/server.py — Source: FastAPI docs + existing VibeVoice app.py generate pattern
import os, io
import soundfile as sf
import numpy as np
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()
SECRET = os.environ.get("API_SECRET", "dev-secret")

SAMPLE_RATE = 24000

def auth(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != SECRET:
        raise HTTPException(401, "Invalid token")

class SynthRequest(BaseModel):
    text: str
    speaker_id: str = "default"   # "default" → persisted Indian voice
    cfg_scale: float = 1.5

@app.get("/voices")
def list_voices() -> list[str]:
    from tts.voice_store import list_voice_ids
    return list_voice_ids()

@app.post("/synthesize")
def synthesize(req: SynthRequest, _ = Depends(auth)) -> Response:
    if len(req.text.split()) < 3:
        raise HTTPException(400, f"Input too short ({len(req.text.split())} words)")
    audio_np = run_vibevoice(req.text, req.speaker_id, req.cfg_scale)  # float32, 24kHz
    buf = io.BytesIO()
    sf.write(buf, audio_np, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return Response(content=buf.getvalue(), media_type="audio/wav")
```

**Canonical HTTP contract (backend-agnostic):**
```
POST /synthesize
Authorization: Bearer <token>
Content-Type: application/json

{ "text": "<spoken text>", "speaker_id": "default", "cfg_scale": 1.5 }

→ 200  Content-Type: audio/wav   <raw WAV bytes, 24kHz PCM16>
→ 400  { "detail": "Input too short (2 words)" }
→ 401  { "detail": "Invalid token" }
```

To swap from Colab to Modal: change `ENDPOINT_URL` env var in the orchestrator. Nothing else changes.

### Pattern 2: cloudflared Tunnel Startup (INFRA-01)

**What:** Start FastAPI in a background thread; start cloudflared tunnel; extract public URL.

```python
# Colab cell — run after defining `app` in server.py
import subprocess, threading, time, uvicorn

def _run():
    uvicorn.run("tts.server:app", host="0.0.0.0", port=8000)

threading.Thread(target=_run, daemon=True).start()
time.sleep(2)  # wait for uvicorn

proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
    stderr=subprocess.PIPE, text=True
)
for line in proc.stderr:
    if "trycloudflare.com" in line:
        public_url = line.strip().split()[-1]
        print("TTS endpoint:", public_url)  # paste into orchestrator ENDPOINT_URL
        break
# ponytail: URL is ephemeral per Colab session; token is stable (Colab Secret)
```

### Pattern 3: Text Normalizer + raw→spoken Map (AUDIO-04)

**What:** Normalize script to spoken form; preserve a per-token `raw→spoken` mapping for caption use.
**Why mapping matters:** Phase 2 (WhisperX) receives the spoken form; Phase 4 (Remotion captions) displays the raw form. The map bridges them.

```python
# tts/normalizer.py
# Source: nemo-text-processing docs + NeMo WFST architecture
import re
from nemo_text_processing.text_normalization.normalize import Normalizer

_normalizer = Normalizer(input_case='cased', lang='en')

# Semiotic spans: dates, currency, ordinals, percentages, URLs, numbers
_SPAN_RE = re.compile(
    r'\$[\d,]+(?:\.\d+)?'       # currency: $42.50
    r'|(?:\d+(?:,\d{3})*(?:\.\d+)?%)'  # percentage: 25%
    r'|(?:\b\d{1,2}/\d{1,2}/\d{2,4}\b)'  # date: 4/7/2026
    r'|(?:https?://\S+)'        # URL
    r'|(?:\b\d+(?:st|nd|rd|th)\b)'  # ordinal: 3rd
    r'|(?:\b[\d,]+(?:\.\d+)?\b)'    # bare number: 42
)

def normalize(raw_text: str) -> tuple[str, list[dict]]:
    """
    Returns (spoken_text, word_map).
    word_map: [{"raw": "25%", "spoken": "twenty five percent", "start_word": 3}]
    Raises ValueError if input < 3 words.
    ponytail: span regex covers common cases; edge cases (e.g. "3.14" as Pi) go to NeMo
    """
    words = raw_text.split()
    if len(words) < 3:
        raise ValueError(f"Input too short: {len(words)} words (minimum 3)")

    word_map: list[dict] = []
    spoken_tokens: list[str] = []
    i = 0
    for w_idx, token in enumerate(words):
        m = _SPAN_RE.fullmatch(token.strip('.,;:!?'))
        if m:
            spoken_form = _normalizer.normalize(token, verbose=False)
            if spoken_form != token:
                word_map.append({
                    "raw": token,
                    "spoken": spoken_form,
                    "start_word": w_idx,
                })
                spoken_tokens.append(spoken_form)
                continue
        spoken_tokens.append(token)

    return " ".join(spoken_tokens), word_map
```

> **Critical:** The spoken text returned here is what gets passed to the TTS AND to `whisperx.align()`.
> The `word_map` is stored alongside `timeline.json` for Phase 4 caption rendering (raw display, spoken alignment).

### Pattern 4: Voice Persistence (AUDIO-03, AUDIO-05)

**What:** The 1.5B community fork conditions on a raw reference audio file at inference time (not a pre-cached `.pt`). Persisting the Indian voice across Colab sessions = commit the reference audio to the git repo.

```
# One-time setup:
# 1. Record/source a clean 5-15s Indian-accent clip (mono, 16kHz or 24kHz, WAV)
# 2. Save to voices/default_indian.wav in this repo
# 3. git add voices/default_indian.wav && git commit

# On every Colab restart (after git clone):
# The file is already there. FastAPI server.py loads it at startup as speaker_id="default".
```

For the 0.5B model (if using that instead of 1.5B for speed), `in-Samuel_man.pt` already exists at
`VibeVoice/demo/voices/streaming_model/in-Samuel_man.pt` and is committed to the repo. It can be
used directly as the default Indian voice without any cloning step.

**AUDIO-05 persistence contract:**
```python
# tts/voice_store.py
DEFAULT_VOICE_PATH = os.path.join(os.path.dirname(__file__), "..", "voices", "default_indian.wav")

def get_voice_path(speaker_id: str) -> str:
    if speaker_id == "default":
        return DEFAULT_VOICE_PATH
    # ... enumerate demo/voices/ for others
```

### Anti-Patterns to Avoid

- **Gradio `/predict` as the TTS API:** Component-position-dependent, incompatible with Modal/RunPod, breaks when UI changes. Use FastAPI.
- **Using `num2words` alone:** It converts bare numbers only. `$42.50`, `25%`, `July 4th` all pass through unchanged and crash wav2vec2 alignment.
- **Deriving `durationSec` from the last word's end timestamp:** Always read actual audio duration with `soundfile.info(path).duration` or `librosa.get_duration(path=path)`. Trailing silence is real.
- **Not normalizing before WER check (Phase 2 concern):** Phase 1's normalizer must output the exact string passed to alignment — document this contract explicitly so Phase 2 doesn't re-normalize independently.
- **Storing reference audio only in Colab's `/content/`:** That directory evaporates on session timeout. Commit the file to the repo.
- **Using pyngrok:** Requires an account/authtoken; free tier has a 1-agent limit. cloudflared Quick Tunnel needs no account.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Number/date/currency → spoken words | Regex + lookup table | `nemo-text-processing` Normalizer | 15+ semiotic classes (DATE, MONEY, ORDINAL, ELECTRONIC, MEASURE…); production-tested by NVIDIA; regex misses "July 4th, 2026 at 3:30 PM" |
| HTTP tunnel from Colab | SSH reverse tunnel / manual port forward | cloudflared Quick Tunnel | One command, no account, HTTPS, works across all Colab GPU tiers |
| WAV encoding | Manual byte packing | `soundfile.write()` | Handles PCM16/float32, sample rate tagging, proper RIFF headers |

---

## Common Pitfalls

### Pitfall 1: NeMo Normalizer on Windows (dev machine)

**What goes wrong:** `pip install nemo-text-processing` on Windows fails — `pynini` has no Windows wheel; the `pynini-2.1.7` manylinux wheel is Linux-only.
**Why it happens:** pynini is a C++ OpenFst wrapper; manylinux wheels only target Linux x86_64.
**How to avoid:** Run normalization in the Colab environment (Linux). For local dev/testing on Windows: use `WeTextProcessing` as a stand-in (`pip install WeTextProcessing` — pure Python, Windows-compatible) or run tests inside WSL. Mark this clearly in the test README.
**Warning signs:** `ERROR: Could not find a version that satisfies pynini` on Windows pip.

### Pitfall 2: Gradio Client Contract vs FastAPI Contract

**What goes wrong:** The existing `app.py` uses `gradio_client.Client.predict(text, voice, cfg_scale, api_name="/predict")`. The argument order and names are Gradio-specific. Attempting to use this as the "stable HTTP contract" breaks when adding any UI component.
**How to avoid:** Never expose the Gradio `.predict()` path to the orchestrator. The FastAPI `/synthesize` endpoint is the only machine-to-machine interface.

### Pitfall 3: Short Inputs Passed to VibeVoice

**What goes wrong:** VibeVoice 0.5B returns `None` for `speech_outputs[0]` on inputs under ~3 words (documented in `app.py`: `"input may be too short"`). This bubbles up as a 500 in a raw FastAPI endpoint.
**How to avoid:** The `normalize()` function raises `ValueError` before calling TTS. The FastAPI handler catches it and returns HTTP 400 with a clear message. This guard lives in `normalizer.py` so it also protects the pipeline's orchestrator from silent null audio.

### Pitfall 4: num2words 0.5.15/0.5.16 Are Compromised

**What goes wrong:** Installing `num2words` without pinning pulls 0.5.15 or 0.5.16, which were supply-chain-compromised packages (July 2025, pulled from PyPI but potentially cached in some mirrors).
**How to avoid:** Pin `num2words==0.5.14` if you use it. This is a non-issue if you use nemo-text-processing as recommended (num2words is not its dependency).

### Pitfall 5: 1.5B Community Fork vs 0.5B Model Interfaces Differ

**What goes wrong:** The 0.5B model uses `process_input_with_cached_prompt(cached_prompt=<.pt dict>)`. The 1.5B community fork conditions on raw audio at inference time. Mixing the two model types without an adapter causes a `KeyError` or shape mismatch.
**How to avoid:** `voice_store.py` abstracts the difference. For 0.5B: `torch.load(voice.pt)` → `cached_prompt` dict. For 1.5B: raw audio path → passed as `reference_audio`. The FastAPI endpoint is model-agnostic; it delegates to `voice_store.get_voice_path(speaker_id)`.

### Pitfall 6: cloudflared URL Is Ephemeral

**What goes wrong:** After a Colab session restarts (idle timeout ~90 min, daily GPU cap), the cloudflared URL changes. The orchestrator config still has the old URL → 404 or connection refused.
**How to avoid:** Expose the URL via an environment variable (`ENDPOINT_URL`) in the orchestrator config. After restarting Colab, copy the new URL into that variable. This is expected behaviour — per PROJECT_PLAN.md §6, Colab is prototype-only. The fix for production is Modal/RunPod (permanent URL), not patching the Colab flow.

---

## Code Examples

### Launch FastAPI + cloudflared on Colab (complete cell)

```python
# Source: cloudflared docs + uvicorn docs
import subprocess, threading, time, uvicorn

def _run_server():
    uvicorn.run("tts.server:app", host="0.0.0.0", port=8000, log_level="warning")

threading.Thread(target=_run_server, daemon=True).start()
time.sleep(3)

proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
    stderr=subprocess.PIPE, text=True
)
for line in proc.stderr:
    if "trycloudflare.com" in line:
        ENDPOINT_URL = line.strip().split()[-1]
        print("Set ENDPOINT_URL =", ENDPOINT_URL)
        break
```

### Calling the Endpoint from the Orchestrator

```python
# Source: httpx docs + our /synthesize contract
import httpx, os

ENDPOINT_URL = os.environ["ENDPOINT_URL"]  # from Colab output above
API_SECRET   = os.environ["API_SECRET"]

def synthesize_audio(spoken_text: str, speaker_id: str = "default") -> bytes:
    """Returns raw WAV bytes. Raises on non-200."""
    r = httpx.post(
        f"{ENDPOINT_URL}/synthesize",
        json={"text": spoken_text, "speaker_id": speaker_id, "cfg_scale": 1.5},
        headers={"Authorization": f"Bearer {API_SECRET}"},
        timeout=120.0,  # TTS can take 30-90s for long scripts
    )
    r.raise_for_status()
    return r.content  # write to disk: open("out.wav","wb").write(r.content)
```

### NeMo Normalizer Setup

```python
# Source: nemo-text-processing PyPI + NVIDIA NeMo docs
from nemo_text_processing.text_normalization.normalize import Normalizer

# ponytail: load once at module level; WFST compilation is slow on first call
_normalizer = Normalizer(input_case='cased', lang='en')

spoken = _normalizer.normalize("I owe $42.50, which is 25% of the total.", verbose=False)
# → "I owe forty two dollars fifty cents, which is twenty five percent of the total."
```

---

## timeline.json Schema (Canonical — Phase 1 Defines This)

Phase 1 is where this schema is **documented as the final contract**. Every downstream phase reads this
file; no phase generates it differently. The schema below is canonical — Phase 2's `02-RESEARCH.md`
already assumes it (adding only `alignMethod`/`alignedAt` to `meta`).

```jsonc
{
  "audio": {
    "path":        "out.wav",        // relative to job working directory
    "sampleRate":  24000,            // VibeVoice outputs 24kHz; always int
    "durationSec": 42.7              // from soundfile.info().duration, NOT from word timestamps
  },
  "words": [
    {
      "w":          "Hello",         // spoken word (normalized form)
      "start":      0.31,            // seconds, float, 3dp
      "end":        0.62,
      "speaker":    1,               // 1-indexed; default 1 for single-speaker
      "confidence": 0.97             // optional; present when aligner returns score
    }
  ],
  "sentences": [
    {
      "idx":        0,               // 0-indexed
      "text":       "Hello world.",  // spoken sentence text
      "start":      0.31,
      "end":        3.90,
      "speaker":    1,
      "wordRange":  [0, 8]           // half-open: words[0..8) — populated by Phase 2
    }
  ],
  "scenes": [],                      // populated by Phase 3; empty array until then
  "meta": {
    "lang":         "en",
    "wer":          0.03,            // populated by Phase 2 WER guard; null until then
    "generator":    "vibevoice-1.5B",// or "vibevoice-0.5B"
    "alignMethod":  null,            // populated by Phase 2: "whisperx-forced" | "whisper-timestamped-fallback"
    "alignedAt":    null             // populated by Phase 2: ISO8601 UTC timestamp
  }
}
```

**Phase 1 produces:** `audio` block (path, sampleRate, durationSec) + empty `words[]`, `sentences[]`, `scenes[]`, and `meta` with `generator` only. Phase 2 fills in `words[]`, `sentences[]`, `meta.wer`, `meta.alignMethod`, `meta.alignedAt`.

**Invariants (all phases must respect):**
- `durationSec` always comes from the actual audio file, never from the last word's `end` timestamp
- `wordRange` is half-open: `words[wordRange[0] : wordRange[1]]`
- `words[].w` contains the **spoken** form (normalized); raw form is in `word_map.json` (written by Phase 1 normalizer)
- `scenes[]` start/end are ALWAYS derived from sentence timestamps, never set by an LLM

**word_map.json** (Phase 1 also writes this, alongside `timeline.json`):
```jsonc
[
  { "raw": "25%",    "spoken": "twenty five percent", "start_word": 3 },
  { "raw": "$42.50", "spoken": "forty two dollars fifty cents", "start_word": 7 }
]
```
Phase 4 (Remotion captions) reads `word_map.json` to display raw text while aligning to spoken timestamps.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gradio share link as API | FastAPI + cloudflared Quick Tunnel | 2024–2025 | Contract is stable across backends; no component-order coupling |
| pyngrok (requires account) | cloudflared Quick Tunnel (no account) | 2023 (Cloudflare launched quick tunnels) | Zero-friction Colab tunneling |
| num2words + regex | nemo-text-processing WFST | 2021 (NeMo TN paper) | Full semiotic coverage; no custom grammar code |
| Pre-computed `.pt` prompts only (0.5B) | Raw-audio conditioning at inference (1.5B) | 2024 (community fork) | Voice cloning from any short clip without GPU pre-processing step |

---

## Open Questions

1. **1.5B community fork availability and API stability**
   - What we know: The community fork (`vibevoice-community/VibeVoice`) is referenced in `colab_1p5b_tts.ipynb` and installs via `pip install -e .`.
   - What's unclear: Whether the fork's `demo/gradio_demo.py` exposes the same `process_input_with_cached_prompt` API or a different raw-audio conditioning API. This affects `voice_store.py` implementation.
   - Recommendation: Before writing `voice_store.py`, clone the fork and read its `demo/gradio_demo.py` and processor. Decide: use 0.5B with `in-Samuel_man.pt` (simpler, no cloning) OR 1.5B (voice cloning from audio). If AUDIO-03 is lower priority, start with 0.5B.

2. **NeMo normalizer on Windows for local dev/tests**
   - What we know: pynini has no Windows wheel; NeMo install fails on Windows.
   - What's unclear: Whether the project's test suite runs on Windows (developer machine) or only in Colab/WSL.
   - Recommendation: Gate NeMo normalization tests with `pytest.mark.skipif(platform.system() == "Windows", ...)` and document `WeTextProcessing` as the Windows-compatible stand-in. Tests that test the normalization contract (input→output) can mock the normalizer on Windows.

3. **Multi-speaker output format from VibeVoice 1.5B**
   - What we know: Phase 2's research flags this as deferred to Phase 1 to clarify. VibeVoice supports up to 4 speakers.
   - What's unclear: Does the 1.5B model output per-speaker sequential WAV segments or a single interleaved mix? If interleaved, Phase 2 needs pyannote diarization.
   - Recommendation: For v1 Phase 1, use single-speaker only (default Indian voice). Multi-speaker is a Phase 1.1 or Phase 7 concern. Document it as out of scope for Phase 1.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `tests/conftest.py` (Wave 0 gap) |
| Quick run command | `pytest tts/tests/ -x -q` |
| Full suite command | `pytest tts/tests/ -v` |
| Estimated runtime | ~10 seconds (normalizer tests are CPU-only; server tests use httpx TestClient, no real model call) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `POST /synthesize` returns `audio/wav` with 200 (mock TTS) | integration (TestClient) | `pytest tts/tests/test_server.py::test_synthesize_returns_wav -x` | ❌ Wave 0 gap |
| INFRA-01 | `POST /synthesize` with bad token returns 401 | integration | `pytest tts/tests/test_server.py::test_auth_rejects_bad_token -x` | ❌ Wave 0 gap |
| AUDIO-01 | Model generate call returns non-empty numpy array (integration smoke, short text, real model) | smoke | `pytest tts/tests/test_server.py::test_generate_short_text -x -m smoke` | ❌ Wave 0 gap |
| AUDIO-02 | `GET /voices` returns list containing an Indian voice | unit | `pytest tts/tests/test_server.py::test_voices_includes_indian -x` | ❌ Wave 0 gap |
| AUDIO-03 | Voice cloning: after uploading reference clip, new voice_id appears in `GET /voices` | integration | `pytest tts/tests/test_server.py::test_clone_voice_registered -x` | ❌ Wave 0 gap |
| AUDIO-04 | `normalize("I owe $42.50")` returns spoken form with no digit-only tokens | unit | `pytest tts/tests/test_normalizer.py::test_currency_expanded -x` | ❌ Wave 0 gap |
| AUDIO-04 | `normalize("ok")` raises ValueError (< 3 words) | unit | `pytest tts/tests/test_normalizer.py::test_short_input_rejected -x` | ❌ Wave 0 gap |
| AUDIO-04 | `normalize(text)` returns word_map with correct raw→spoken entries | unit | `pytest tts/tests/test_normalizer.py::test_word_map_populated -x` | ❌ Wave 0 gap |
| AUDIO-05 | `voice_store.get_voice_path("default")` returns path that exists on disk | unit | `pytest tts/tests/test_voice_store.py::test_default_indian_voice_exists -x` | ❌ Wave 0 gap |

### Nyquist Sampling Rate

- **Minimum sample interval:** After every committed task → run: `pytest tts/tests/ -x -q`
- **Full suite trigger:** Before merging the final task of the Phase 1 plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~10 seconds (unit/integration, no model call)
- **Smoke tests** (`-m smoke`, require real model): run manually on Colab before closing the phase

### Wave 0 Gaps (must be created before implementation)

- [ ] `tts/tests/conftest.py` — fixtures: mock TTS function, sample WAV bytes (2s of silence at 24kHz), test API secret
- [ ] `tts/tests/test_server.py` — covers INFRA-01, AUDIO-01, AUDIO-02, AUDIO-03
- [ ] `tts/tests/test_normalizer.py` — covers AUDIO-04 (all semiotic classes + short-input rejection + word_map)
- [ ] `tts/tests/test_voice_store.py` — covers AUDIO-05 (default path exists, list voices)
- [ ] `pytest` install: `pip install pytest httpx` (httpx required for FastAPI TestClient)

---

## Sources

### Primary (HIGH confidence)

- `VibeVoice/app.py` (this repo) — generate API, voice loading pattern, `process_input_with_cached_prompt`
- `VibeVoice/demo/realtime_model_inference_from_file.py` — full generation pipeline, `VoiceMapper`, `.pt` loading
- `VibeVoice/colab_gpu_tts.ipynb` / `colab_1p5b_tts.ipynb` — Colab patterns for 0.5B and 1.5B
- `VibeVoice/demo/voices/streaming_model/` — `in-Samuel_man.pt` confirmed present (Indian male voice, 0.5B)
- `.planning/phases/02-alignment-engine/02-RESEARCH.md` — timeline.json schema reference; confirmed wav2vec2 no-digits constraint (drives AUDIO-04 requirement)
- [PyPI: nemo-text-processing 1.2.0](https://pypi.org/project/nemo-text-processing/) — version/date confirmed
- [PyPI: pynini manylinux wheel availability](https://pypi.org/project/pynini/) — Linux install confirmed
- [Cloudflare Quick Tunnels](https://try.cloudflare.com/) — no-account HTTPS tunnel confirmed
- [FastAPI security docs](https://fastapi.tiangolo.com/tutorial/security/first-steps/) — HTTPBearer pattern

### Secondary (MEDIUM confidence)

- [NeMo WFST Text Normalization semiotic classes](https://docs.nvidia.com/nemo-framework/user-guide/24.12/nemotoolkit/nlp/text_normalization/wfst/wfst_text_normalization.html) — class coverage verified
- Research sub-agent (July 2026): cloudflared vs pyngrok comparison, num2words compromise, WeTextProcessing coverage matrix

### Tertiary (LOW confidence — needs validation)

- 1.5B community fork API surface (`process_input_with_cached_prompt` vs raw audio conditioning): inferred from `colab_1p5b_tts.ipynb` notebook structure; **must verify** by reading `vibevoice-community/VibeVoice` source before implementation
- NeMo tagger `verbose=True` token-alignment claim: architecture knowledge from paper, not tested programmatically

---

## Metadata

**Confidence breakdown:**
- Standard stack (FastAPI, uvicorn, soundfile, cloudflared): HIGH — documented, pip-installable, actively maintained
- nemo-text-processing: HIGH for install/coverage; MEDIUM for token-level mapping API (internal architecture, not public API)
- VibeVoice 0.5B API and Indian voice: HIGH — code in repo, `in-Samuel_man.pt` confirmed
- VibeVoice 1.5B community fork API: LOW — inferred from notebook, not code-verified
- timeline.json schema: HIGH — consistent with Phase 2 research; all invariants traced from PROJECT_PLAN.md §1
- cloudflared tunnel: HIGH — official documentation verified

**Research date:** 2026-07-09
**Valid until:** 2026-08-09 (30 days; re-check nemo-text-processing version and 1.5B fork URL before execution)
