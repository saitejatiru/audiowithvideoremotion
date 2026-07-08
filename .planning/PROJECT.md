# Synced Explainer Video Generator

## What This Is

A pipeline that turns a text script into a finished explainer video: VibeVoice narration,
visuals timed to the words, word-level captions, metadata stripped — delivered from one simple
Gradio page. For creators who want narrated explainer/educational videos without manual editing
or hand-timing.

## Core Value

The narration, on-screen visuals, and captions are **perfectly synced to the audio**. If
everything else is mediocre but sync is tight, it still works. If sync is off, nothing else matters.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Script → VibeVoice narration audio, with selectable/clonable voice (incl. Indian)
- [ ] Word-level timing via forced alignment (WhisperX) + ASR-WER verification guard
- [ ] LLM storyboard: scene / visual / on-screen-text per sentence (Minimax/DeepSeek/Kimi)
- [ ] Remotion video render driven by a `timeline.json` contract, synced to audio
- [ ] Word-level captions rendered in-video
- [ ] Metadata strip / de-fingerprint via ffmpeg + web faststart
- [ ] Simple Gradio platform: script in → video out
- [ ] GPU pipeline runs on Colab now, swappable to Modal/RunPod via one HTTP contract

### Out of Scope

- Real-time / streaming generation — batch is fine for explainer videos
- Manual video-editor UI — v1 is auto-generated only
- Accounts / billing / persistent multi-user hosting — this is a prototype
- Explicit emotion-control knob — expressiveness comes from text + reference clip, not a parameter

## Context

- Built around **VibeVoice**. The 0.5B streaming model works; the 1.5B community fork adds voice
  cloning from a reference clip. Audio already generates on Colab GPU this session.
- **Language split is fundamental:** TTS + alignment are Python; Remotion is Node/React. They
  integrate by passing JSON files, not by sharing a runtime.
- **The make-or-break risk is audio→word timestamps.** It must be de-risked first (Phase 2) before
  any video work — a wrong timeline makes every visual worthless.
- Existing session assets: `VibeVoice/app.py` (Colab+CPU TTS), Colab notebooks (0.5B & 1.5B),
  HF Space `saitejatirunagari/audio_and_video`, and `PROJECT_PLAN.md` (the design doc this seeds from).

## Constraints

- **Hardware**: No local GPU → GPU stages run on Colab (prototype) / Modal-RunPod (prod). Design the
  GPU stage as a swappable HTTP endpoint from day one.
- **Tech stack**: VibeVoice (TTS), WhisperX (forced align), Remotion (video), ffmpeg (post), Gradio (UI).
- **TTS limits**: VibeVoice is unstable on numbers/code/symbols and inputs under ~3 words → normalize
  text before synthesis; keep a raw→spoken map for captions.
- **Hosting**: HF free tier now paywalls Docker/Gradio Space hosting; Colab share links are ephemeral
  and sleep when idle.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Forced alignment (WhisperX) + ASR-WER verify as primary; whisper-timestamped as fallback | We own the exact script — re-transcribing adds drift on accents/jargon | — Pending |
| LLM decides content, forced alignment decides timing | Keeps sync deterministic; the LLM never sets durations | — Pending |
| Colab GPU now, behind a swappable HTTP contract | Free to start; avoid Colab lock-in for production | — Pending |
| Extend the existing Gradio app for the platform | Reuse a working UI; fastest path to script-in/video-out | — Pending |
| Captions rendered inside Remotion (not burned in later) | Avoids a fragile post-render burn-in step | — Pending |

---
*Last updated: 2026-07-08 after initialization*
