# Colab Verification Checklist — Phases 1, 2 & 3

Everything that can only run on Colab (GPU/Linux) or needs API keys, collected in one place.
The code is complete and unit-verified on Windows; these steps confirm the GPU/Linux/API
runtime behaviors and **unblock Phase 4** (the Phase 2 isolation gate is the gate).

Run on a **T4 GPU** Colab runtime.

---

## 0. Get the code onto Colab (prerequisite)

The `tts/`, `align/`, and `storyboard/` code lives only on your machine + local git.
Push it, then clone on Colab.

**On Windows (once):**
```bash
git remote add origin <your-github-repo-url>
git push -u origin master
```

**On Colab (each session):**
```python
!git clone <your-github-repo-url> audio
%cd audio
# model code + voices (in-Samuel_man.pt) — NOT in the project repo (separate clone):
!git clone https://github.com/microsoft/VibeVoice.git
import sys; sys.path.insert(0, ".")   # so `import tts`, `import align`, `import storyboard` resolve
```

---

## 1. Install dependencies
```python
# Phase 1
!pip install -q fastapi "uvicorn[standard]" soundfile requests nemo-text-processing
# Phase 2 (torch/torchaudio come preinstalled on Colab)
!pip install -q -r align/requirements.txt   # whisperx, whisper-timestamped, jiwer, whisper-normalizer, librosa
# Phase 3
!pip install -q openai json-repair
```

---

## 2. Phase 1 checks (3)

**2a. NeMo text normalization — AUDIO-04**
```python
!pytest tts/tests/test_normalizer.py -q          # expect: 4 passed (were skipped on Windows)
# quick manual check:
from tts.normalizer import normalize
spoken, wm = normalize("I owe $42.50 today")
assert "$" not in spoken and any(e["raw"] == "$42.50" for e in wm)
```

**2b. Live HTTP endpoint + cloudflared tunnel — INFRA-01**
```python
from tts.colab_launch import launch
url = launch()          # prints: ENDPOINT_URL = https://xxx.trycloudflare.com
# then curl POST {url}/synthesize with a Bearer token + 3+ word text → expect non-empty audio/wav
```

**2c. Real GPU synthesis + persisted default voice — AUDIO-01 / AUDIO-05**
- Make two back-to-back `POST /synthesize` calls with `speaker_id="default"`.
- Expect: both return WAV voiced by `in-Samuel_man` (Indian male), no re-upload between calls.

---

## 3. Phase 2 check — the Phase 4 gate (1)

**3a. Isolation gate — must pass before any Remotion/video work**
```python
import os
os.environ["TEST_CLIP_PATH"] = "/content/audio/sample.wav"   # a real 5-30s English speech WAV
!python align/isolation_test.py
```
Expected output:
```
KNOWN-GOOD: PASS   (alignMethod=whisperx-forced, wer < 0.08, durationSec > words[-1].end)
FALLBACK:   PASS   (alignMethod=whisper-timestamped-fallback, all words have {w,start,end,speaker})
PHASE 2 ISOLATION GATE: PASSED
```
- If WER lands above 0.08 on an Indian-accent clip (documented accent penalty): set the verifier's
  `wer_model_size="large-v2"` and re-run.

**3b. (optional) Full GPU test suite**
```python
!pytest align/tests/ -q      # with TEST_CLIP_PATH set, the Windows-skipped tests now run
```

---

## 4. Phase 3 check — LLM storyboard integration (2)

**4a. Real LLM storyboard call — STORY-01 / STORY-02**
```python
import os, json

# Set your LLM API key (DeepSeek is cheapest)
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_API_KEY"]  = "<your-deepseek-api-key>"
os.environ["LLM_MODEL"]    = "deepseek-chat"

# Load a real timeline.json from Phase 2 (after 3a passes)
with open("timeline.json") as f:
    timeline = json.load(f)

from storyboard.pipeline import storyboard_pipeline
result = storyboard_pipeline(timeline)

print(f"Scenes generated: {len(result['scenes'])}")
print(f"Sentences count:  {len(result['sentences'])}")
assert len(result["scenes"]) == len(result["sentences"]), "Scene count must match sentence count"

# Verify scene boundaries match sentence boundaries (STORY-03)
for scene, sent in zip(result["scenes"], result["sentences"]):
    assert scene["start"] == sent["start"], f"Scene {scene['idx']} start mismatch"
    assert scene["end"] == sent["end"], f"Scene {scene['idx']} end mismatch"

print("✅ STORY-01/02/03: ALL PASSED — scenes generated, validated, timing from sentences")
```

**4b. Fallback resilience — STORY-02**
```python
# Test with an invalid API key to trigger fallback
import os
os.environ["LLM_API_KEY"] = "invalid-key-test"

from storyboard.pipeline import storyboard_pipeline
result = storyboard_pipeline(timeline)

assert len(result["scenes"]) == len(result["sentences"]), "Fallback must still produce correct count"
assert all(s["visual"]["type"] == "bullet" for s in result["scenes"]), "Fallback should produce bullets"
print("✅ STORY-02 fallback: PASSED — graceful degradation to bullet scenes")
```

---

## 5. Full pipeline E2E — Phases 4-6 (after sections 3-4 pass)

**5a. Setup (Node + ffmpeg + deps)**
```python
!apt-get -qq install -y ffmpeg
!npm install --prefix video --silent          # Remotion deps (Node 20 preinstalled on Colab)
!pip install -q openai json-repair tenacity gradio
```

**5b. One-shot script→video run — VIDEO-01/02/03, POST-01/02, PLAT-02**
```python
import os
os.environ["LLM_API_KEY"] = "<your-deepseek-api-key>"   # from section 4

from orchestration.orchestrator import orchestrate_video
final = None
for status, video in orchestrate_video(
    "Machine learning helps computers learn patterns from data without explicit programming.",
    "default", ""):
    print(status)
    if video: final = video
assert final and final.endswith("final.mp4")
```
Verify on the output:
- Video plays; captions appear word-by-word in sync with narration (VIDEO-01/02)
- `!ffprobe -v quiet -print_format json -show_format {final}` → no custom tags (POST-01)
- Duration matches audio length within a frame (VIDEO-03)

**5c. Gradio UI — PLAT-01**
```python
os.environ["GRADIO_SHARE"] = "1"
!python app.py    # open the share URL, generate a video from the browser
```

---

## What passing these unblocks

| Result | Meaning |
|--------|---------|
| Section 2 all pass | Phase 1 fully verified (currently `human_needed`) |
| Section 3a prints "GATE: PASSED" | Phase 2 fully verified → **Phase 4 (Remotion) may begin** |
| Section 4a prints "ALL PASSED" | Phase 3 fully verified — LLM integration confirmed |
| Section 4b prints "fallback: PASSED" | Phase 3 resilience verified — pipeline crash-proof |
| Section 5b produces a playable final.mp4 | Phases 4-6 verified — **the product works end-to-end** |

Until 3a passes on Colab, Phase 4 stays BLOCKED by design — a wrong timeline makes every video frame wrong.
