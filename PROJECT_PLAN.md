# Script → Synced Explainer Video — Product Plan

**Outcome:** Give a script (text). Get back a finished explainer video: VibeVoice narration,
visuals that change in time with the words, word-level captions, metadata stripped, downloadable
from one simple web page.

**One-line architecture principle:** *The LLM decides WHAT appears. Forced alignment decides WHEN.
Remotion just lays frames to a timeline it's handed.* Sync is a data problem, not a rendering problem.

---

## 1. The sync problem (the crux) — how we actually solve it

We control the script text, so we do **forced alignment**, not ASR transcription.

| Option | What it does | Verdict |
|--------|--------------|---------|
| whisper-timestamped (your idea) | Transcribes audio, derives word times from attention | Works, but re-transcribes text we already have → drift on accents/jargon. **Fallback.** |
| WhisperX | Whisper + wav2vec2 forced alignment, batched, GPU-fast | **Primary.** Robust word boundaries; align against our script. |
| torchaudio MMS/Wav2Vec2 forceAlign / aeneas / MFA | Pure forced alignment of known text | Great fidelity; heavier setup. Alternative to WhisperX. |

**The pipeline for timing:**
1. **Normalize script** before TTS (expand numbers, dates, symbols; strip code) — VibeVoice explicitly
   misbehaves on those. Keep a `raw → spoken` map so captions can show raw text while alignment uses spoken.
2. **Generate audio** (VibeVoice, Colab/GPU).
3. **Forced-align** the *spoken* script to the audio → `words[]` with `start`/`end` (+ speaker for multi-speaker).
4. **Verify** with ASR (Whisper) → compare transcript to script (WER). If WER > threshold, the TTS
   deviated → regenerate audio or fall back to ASR-based timestamps. This guard is what makes it production-safe.
5. Emit **`timeline.json`** — the single contract every downstream stage reads.

### timeline.json (the contract — define this first, everything hangs off it)
```jsonc
{
  "audio": { "path": "out.wav", "sampleRate": 24000, "durationSec": 42.7 },
  "words": [ { "w": "Hello", "start": 0.31, "end": 0.62, "speaker": 1 } ],
  "sentences": [ { "idx": 0, "text": "...", "start": 0.31, "end": 3.9, "speaker": 1, "wordRange": [0, 8] } ],
  "scenes": [ { "idx": 0, "sentenceRange": [0,1], "start": 0.31, "end": 7.2,
                "onScreenText": "...", "visual": {"type":"bullet|image|code","query":"..."} } ],
  "meta": { "lang": "en", "wer": 0.03, "generator": "vibevoice-1.5B" }
}
```
Rule: **durations come from `audio`/alignment, never from LLM guesses.** `durationInFrames = ceil(durationSec * fps)`.

---

## 2. Component architecture

```
[Web UI]  →  [Orchestrator API (FastAPI)]  →  job queue
                     │
     ┌───────────────┼────────────────────────────────┐
     ▼               ▼                ▼                 ▼
 (a) TTS         (b) Align+Verify  (c) Storyboard    (d) Render
 VibeVoice/GPU   WhisperX/GPU      LLM (Minimax/      Remotion (Node +
 → out.wav       → timeline.json   DeepSeek/Kimi)     headless Chromium)
                                   → scenes[]          → video.mp4
                                                            │
                                                            ▼
                                                   (e) Post: ffmpeg
                                                   strip metadata + faststart
                                                            │
                                                            ▼
                                                     download / preview
```

**Language split is real:** TTS/alignment are Python; Remotion is Node/React. The orchestrator shells
out to `npx remotion render` with `--props timeline.json`. Don't try to unify languages — pass JSON files.

---

## 3. LLM ideation (Minimax M3 / DeepSeek / Kimi K2.6)

Role: **storyboard only.** Input = script + `sentences[]`. Output = `scenes[]` (what's on screen per
sentence: bullet text, image/b-roll keyword, code block, transition). It does **not** set timing —
scene `start`/`end` are derived from the sentences' aligned times. Content from LLM, timing from audio.

- Use one model as primary, others as fallback/ensemble (they're all OpenAI-compatible APIs).
- Force **structured JSON output** against a schema; reject/repair on parse failure.
- Cap scenes to sentence boundaries so a scene can never straddle a word mid-utterance.

---

## 4. Remotion rendering

- Composition reads `timeline.json` as props. `<Audio src={out.wav}>` for narration.
- `durationInFrames = ceil(durationSec * fps)`, `fps = 30`.
- Word captions via `@remotion/captions` (`createTikTokStyleCaptions`) fed `words[]`; each word's
  appear frame = `round(start * fps)`.
- Scenes swap at sentence boundaries; use `<Sequence from={round(start*fps)} durationInFrames=...>`.
- Embed fonts (`@remotion/google-fonts` or local) so captions render identically headless.
- Consult the **remotion-best-practices** skill before writing compositions.

---

## 5. Post-processing (captions + metadata strip)

- Captions: rendered *in* Remotion (styled, synced) — no separate burn-in step needed.
- Strip metadata / de-fingerprint:
  ```bash
  ffmpeg -i render.mp4 -map_metadata -1 -map_chapters -1 \
         -c copy -movflags +faststart clean.mp4
  ```
  `-map_metadata -1` drops container tags (incl. any encoder/comment tag); `+faststart` keeps it
  web-streamable. Re-encode only if a stream-level tag must go. (Benign: branding/privacy.)

---

## 6. Hosting reality (forward-deployed honesty)

- **Colab = prototype only.** URL churns, sleeps at ~90 min, ToS-shaky as a server. Fine to build/demo on.
- **Product needs a persistent GPU** for TTS+alignment: Modal, RunPod, or an HF Inference Endpoint.
  Remotion render is CPU/Chromium — runs on a cheap box or the same host.
- Design the orchestrator so the GPU stage is a swappable endpoint (Colab today, Modal later — same HTTP contract).

---

## 7. Phased roadmap

| Phase | Goal | Depends on |
|-------|------|-----------|
| 1. Contracts & text prep | Define `timeline.json`; script normalizer (`raw→spoken` map); TTS service behind stable HTTP | — |
| 2. Alignment engine | WhisperX forced align + ASR-WER verifier → `timeline.json`; fallback to whisper-timestamped | 1 |
| 3. Storyboard | LLM (Minimax/DeepSeek/Kimi) script+sentences → `scenes[]`, schema-validated | 1 |
| 4. Remotion render | Composition consuming timeline+scenes; word captions; audio sync; fonts | 2,3 |
| 5. Post-process | ffmpeg metadata strip + faststart; thumbnail | 4 |
| 6. Platform | Simple web UI + orchestrator API + job queue tying 1–5 together | 2–5 |
| 7. Hardening | Concurrency, retries, observability, cleanup, edge cases below | 6 |

Critical path = **Phase 2** (sync). Everything visual is worthless if timing is wrong. Build/verify it in isolation with a known clip before touching Remotion.

---

## 8. Edge cases (checked explicitly)

**Text / TTS**
- Numbers, dates, currency, %, units → normalize to words pre-TTS; keep raw for captions.
- Code, formulas, emojis, URLs → strip/normalize (VibeVoice unstable on these).
- Input < 3 words → VibeVoice unstable; pad or reject with a clear error.
- Very long script (→90 min) → chunk TTS + align per chunk, then offset-merge timelines.
- Non-English → alignment model must match language; wrong model = garbage timings.
- Indian/accented voice → prefer forced alignment (ASR WER high); this is *why* we don't lead with transcription.

**Sync / alignment**
- TTS skips/adds/mispronounces words → ASR-WER guard catches it → regenerate or fallback.
- Repeated words / homographs → forced alignment handles; fuzzy text-match would not.
- Long silences/pauses → gaps in `words[]`; captions must not hang; scenes pad gracefully.
- Multi-speaker (VibeVoice up to 4) → per-word `speaker`; caption color/position per speaker.

**Render / timing**
- Audio vs video duration mismatch → always derive `durationInFrames` from real audio length; last scene extends to audio end.
- fps rounding drift over long videos → compute frames from seconds per element, never accumulate.
- Font missing headless → captions shift/box-glyph; embed fonts, pin versions.
- Chromium headless deps on server → libgl/libnss etc. (already handled in our HF Docker base).

**Post / platform**
- `-c copy` metadata strip must not break playback; verify `+faststart` for web.
- Colab session dies mid-job → orchestrator retries; job state persisted; idempotent stages keyed by content hash.
- Concurrency / GPU contention → single queue, one GPU job at a time (prototype); scale out later.
- Storage growth → TTL cleanup of intermediate wavs/frames.
- Reproducibility → fix TTS seed + deterministic Remotion so re-runs match.

**LLM storyboard**
- Malformed JSON → schema validation + one repair retry, else deterministic fallback (plain bullets from sentences).
- Scene straddling a word → clamp scene bounds to sentence boundaries.
- Hallucinated visuals / unsafe imagery → keyword allowlist / safe-search on b-roll.

---

## 9. Recommended tech choices

- Alignment: **WhisperX** (primary), whisper-timestamped (fallback), ASR-WER guard (mandatory).
- Orchestrator: **FastAPI** + a simple queue (RQ/Celery, or in-proc for prototype).
- Video: **Remotion** (`@remotion/captions`, `@remotion/google-fonts`).
- Post: **ffmpeg** (`-map_metadata -1 -movflags +faststart`).
- GPU host: Colab (proto) → **Modal/RunPod** (prod), behind one HTTP contract.
- LLM: OpenAI-compatible client, primary = your pick, others fallback.

## 10. Decisions (locked)
1. **Sync tool:** WhisperX forced align + ASR-WER verify; whisper-timestamped = fallback.
2. **Hosting:** Colab GPU now, behind a stable HTTP contract → swap to Modal/RunPod for prod.
3. **Platform UI:** extend the existing Gradio app.
