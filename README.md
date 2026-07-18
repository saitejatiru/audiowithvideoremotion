# Explainer Video Generator

Turn a plain text script into a **fully narrated, captioned, illustrated explainer video** — automatically. Written for board-exam education content (CBSE Class 10/12: Physics, Chemistry, Biology, Maths), but works for any script.

You paste a script → the pipeline speaks it, times every word, designs scenes, fetches visuals, and renders a synced MP4.

---

## How it works (the pipeline)

Five stages run end to end. Each stage's output feeds the next; the timing decided in stage 2 is authoritative for everything after it, so audio and visuals never drift.

```
script text
   │
   ▼
1. TTS  ──────────  VibeVoice speaks the script → narration.wav
   │                (tts/)
   ▼
2. ALIGN  ────────  WhisperX force-aligns audio to text → per-word timestamps
   │                (align/)   → timeline.json  {words[], sentences[]}
   ▼
3. STORYBOARD  ───  an LLM turns each sentence into a scene (title, bullets,
   │                chart/steps/formula/diagram, emoji)   (storyboard/)
   │                then fetch real visuals per scene:
   │                  • Pixabay illustration/video  (concept scenes)
   │                  • Wikimedia diagram           (labeled science diagrams)
   ▼
4. RENDER  ───────  Remotion (React) draws animated scenes + TikTok-style
   │                captions, synced to the audio → rendered.mp4   (video/, render/)
   ▼
5. POST  ─────────  strip metadata, optimize for web → final.mp4   (post_process/)
```

The whole thing is orchestrated by `orchestration/orchestrator.py`, which is what the Gradio UI (`app.py`) calls.

---

## Repository layout

| Path | What it does |
|---|---|
| `app.py` | Gradio web UI — paste a script, pick voice/subject/grade, generate. |
| `colab_pipeline.ipynb` | **The way you actually run this** — a Colab notebook (needs a GPU). |
| `orchestration/orchestrator.py` | Runs the 5 stages in order, yields progress, hard-stops on failure. |
| `tts/` | VibeVoice text-to-speech. `vibevoice_loader.py` picks the model size; `server.py` is the synth logic + FastAPI backend. |
| `align/` | Forced alignment (WhisperX) + a whisper-timestamped CPU fallback. Produces `timeline.json`. |
| `storyboard/` | LLM scene design (`prompter.py`, `client.py`), validation/repair (`repair.py`, `schema.py`), and visual fetching (`assets.py`). |
| `render/render_bridge.py` | Python → Remotion bridge; copies assets into `video/public/` and shells out to `npx remotion render`. |
| `video/` | The Remotion (React/TypeScript) project. `src/components/SceneRenderer.tsx` and `CaptionRenderer.tsx` are the visuals. |
| `post_process/` | ffmpeg cleanup of the final MP4. |
| `voices/`, `VibeVoice/` | Voice assets and the (git-ignored) VibeVoice model clone. |

---

## Running it (Colab)

This needs a GPU, so it runs on Google Colab, not a laptop.

1. Open `colab_pipeline.ipynb` in Colab.
2. **Runtime → Change runtime type → T4 GPU.**
3. Run cells top to bottom. In **cell 2 (API keys)**, paste:
   - `LLM_API_KEY` — an NVIDIA NIM key from [build.nvidia.com](https://build.nvidia.com) (`nvapi-…`).
     `LLM_MODEL` is set to `meta/llama-3.3-70b-instruct` (verified working on the hosted endpoint).
   - `PIXABAY_API_KEY` — a free key from [pixabay.com/api/docs](https://pixabay.com/api/docs/) (for illustrations/video).
   - **Cell 2 must print `LLM OK` and `PIXABAY OK` before you generate.** If it doesn't, the video degrades to plain text — that's the #1 cause of a bad result.
4. Run the last cell (`app.py`), open the Gradio link, paste a script, Generate.

> **Keys are never committed** — this repo is public, so paste keys into the Colab cell at runtime (they live only in the session).

### Model choice (cell 0)

| `VIBEVOICE_MODEL` | Voice | Fits free T4? |
|---|---|---|
| `0.5B` | fast, fixed voices | yes |
| `1.5B` (default) | **voice cloning** from a reference clip | yes (~7 GB) |
| `Large` | best quality (~9B) | no — needs Colab Pro A100/L4 |

---

## Local development (no GPU)

You can't run TTS locally, but you **can** work on the visuals with live preview:

```bash
cd video && npm install
npm run dev          # Remotion Studio at http://localhost:3000
```

Edit `video/src/components/SceneRenderer.tsx` / `CaptionRenderer.tsx` and see changes instantly. `.claude/launch.json` has this server preconfigured.

Run the Python tests:

```bash
python -m pytest storyboard/ align/ orchestration/ render/ tts/ -q
```

---

## Scene types

The storyboard LLM picks one visual per sentence:

- `bullet` — key points, revealed one by one
- `big-number` — a striking stat, pops in
- `comparison` — two side-by-side panels
- `chart` — animated bars from real values
- `steps` — a numbered process/flow
- `formula` — typeset maths (KaTeX)
- `diagram` — a **real labeled diagram** fetched from Wikimedia (heart, cell, circuit…)
- `image` — a concept illustration

Concept scenes get a Pixabay illustration/video as an animated background; captions are word-highlighted TikTok-style. Every visual **fails soft** — if a fetch or the LLM fails, the scene still renders from its template, so the pipeline never breaks.

---

## Honest status & limitations

- **The visuals are an illustrated, captioned "motion slideshow"**, not true 2D character/diagram animation. Fetched illustrations + animated text + synced captions — good, but not Vyond/After-Effects-style animation.
- **True 2D animation** (flowing diagrams, moving parts) is being explored via **[Manim](https://www.manim.community/)** (the 3Blue1Brown engine) for Physics/Maths scenes — code-driven, local, but a work in progress.
- **Correctness first:** diagrams come only from Wikimedia (human-made), never AI-generated — a wrong labeled diagram is worse than none for exam content.
- **The LLM must authenticate** or you get plain text. Many NVIDIA NIM catalog models (e.g. Kimi K2.6) are self-host-only and 404 on the hosted endpoint — use a model that passes cell 2's smoke test.

---

## Requirements

- **Colab GPU** (T4 free tier works for 0.5B/1.5B).
- **NVIDIA NIM API key** (LLM storyboard) + **Pixabay API key** (visuals) — both free.
- Node.js 20 + the Remotion deps and Python deps — all installed by the notebook's setup cells.
