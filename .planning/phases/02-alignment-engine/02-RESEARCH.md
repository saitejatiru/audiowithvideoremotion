# Phase 2: Alignment Engine — Research

**Researched:** 2026-07-08
**Domain:** Forced alignment, ASR-WER verification, timeline.json schema
**Confidence:** HIGH (core stack), MEDIUM (WER threshold, edge-case mitigations)

---

## Summary

Phase 2 is the critical path for the entire pipeline. Everything downstream (Remotion render,
captions, storyboard timing) is only as good as the word-level timestamps produced here. The
primary tool is **WhisperX 3.8.6** (May 2026), which exposes a two-step API: ASR transcription
(which we skip) and a separable forced-alignment step that accepts a pre-formatted known-transcript
segment list. The alignment step uses a wav2vec2 phoneme model (`WAV2VEC2_ASR_BASE_960H` for
English) to produce sub-100ms-accurate word boundaries.

The mandatory guard is an **ASR-WER check** using `jiwer 4.0.0` and `whisper-normalizer
0.1.12` (OpenAI's `EnglishTextNormalizer`). Normalizing both reference and hypothesis before
computing WER eliminates false-positive failures caused by punctuation, number formatting, and
contractions — so only genuine TTS drift gets flagged. When drift exceeds the threshold (~8%),
the stage regenerates audio (if within retry budget) or falls back to `whisper-timestamped
1.15.9`, which derives word times via Dynamic Time Warping on cross-attention weights without
needing wav2vec2.

The single output contract is `timeline.json`. Its schema is defined in `PROJECT_PLAN.md §1`
and extended here with `alignMethod` and `werScore` in `meta`. Every downstream consumer reads
only this file; the alignment implementation detail is invisible to them.

**Primary recommendation:** Use WhisperX's alignment-only path (bypass its ASR step, inject the
known transcript as a segment dict), run `EnglishTextNormalizer` + `jiwer.wer()` as the guard,
and fall back to `whisper-timestamped` when alignment fails or returns too many NaN-interpolated
timestamps.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ALIGN-01 | Word-level timestamps by forced-aligning known script to audio (WhisperX) | WhisperX `align()` API with pre-formatted known-transcript segments; `WAV2VEC2_ASR_BASE_960H` English model |
| ALIGN-02 | Verify TTS fidelity via ASR-WER; flag/regenerate when drift exceeds threshold | `jiwer.wer()` + `EnglishTextNormalizer`; threshold 0.08 recommended; regenerate-or-fallback policy |
| ALIGN-03 | Emit `timeline.json` (words, sentences, durations, speaker) as canonical contract | Schema defined in PROJECT_PLAN.md §1; extend `meta` with `alignMethod` + `werScore` |
| ALIGN-04 | Fall back to whisper-timestamped when forced alignment fails | `whisper_timestamped.transcribe()`; normalize output into identical `words[]`/`sentences[]` schema |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| whisperx | 3.8.6 | Forced alignment of known transcript to audio; word-level timestamps | Industry standard; wav2vec2 gives sub-100ms accuracy; alignment step is separable from ASR |
| jiwer | 4.0.0 | WER computation between reference script and ASR hypothesis | Fastest Python WER library (RapidFuzz C++ backend); supports composable transforms |
| whisper-normalizer | 0.1.12 | Normalize text before WER (numbers, contractions, titles) | OpenAI's own normalizer; handles the exact tokens VibeVoice mispronounces |
| whisper-timestamped | 1.15.9 | Fallback: word timestamps via DTW cross-attention (no wav2vec2) | Pure-Whisper approach; more robust when wav2vec2 vocabulary mismatch is the failure |
| openai-whisper | latest | ASR model for WER verification pass | Already a dep of whisper-timestamped; use `large-v2` or `turbo` for verification |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torchaudio | ≥2.4 | Provides `WAV2VEC2_ASR_BASE_960H` pipeline (auto-fetched by WhisperX) | Always; it is a WhisperX dep |
| torch | ≥2.0 + CUDA 12.8 | GPU backend for WhisperX + Whisper | On Colab GPU; fall back to `compute_type=int8, device=cpu` for short clips |
| soundfile / librosa | latest | Load 24kHz WAV before passing to WhisperX | WhisperX expects a numpy float32 array at 16kHz; resample from 24kHz |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WhisperX forced-align | Montreal Forced Aligner (MFA) | MFA requires separate lexicon files and a corpus install step; heavier setup for no accuracy gain here |
| WhisperX forced-align | torchaudio MMS/CTC aligner directly | More control but no pre-built English pipeline; re-implements what WhisperX already wraps |
| jiwer | torchmetrics WER | jiwer is simpler, has better normalize API, and doesn't add torch as an extra dep |
| whisper-timestamped | stable-ts | stable-ts has a similar DTW approach; whisper-timestamped has better docs and more VAD options |

**Installation:**
```bash
pip install whisperx==3.8.6 jiwer==4.0.0 whisper-normalizer==0.1.12 whisper-timestamped==1.15.9
# CUDA 12.8 required for GPU; CPU fallback: add --compute_type int8 in WhisperX calls
```

---

## Architecture Patterns

### Recommended Project Structure

```
align/
├── aligner.py          # WhisperX forced-align path (ALIGN-01)
├── verifier.py         # ASR-WER guard (ALIGN-02)
├── fallback.py         # whisper-timestamped fallback (ALIGN-04)
├── schema.py           # timeline.json builder + sentence splitter (ALIGN-03)
└── tests/
    ├── test_aligner.py     # known-clip word-time assertions
    └── test_verifier.py    # WER normalization + threshold logic
```

### Pattern 1: Forced Alignment of a Known Transcript

**What:** Bypass WhisperX ASR; inject the pre-normalized spoken transcript as a segment dict
and call `whisperx.align()` directly.

**When to use:** Always as the primary path (Phase 1 produced the spoken transcript).

```python
# Source: github.com/m-bain/whisperX/issues/649
import whisperx, librosa, numpy as np

DEVICE = "cuda"   # or "cpu" with compute_type="int8"
LANG   = "en"

def align_known_transcript(wav_path: str, spoken_text: str) -> dict:
    # WhisperX expects 16kHz float32 mono
    audio, _ = librosa.load(wav_path, sr=16000, mono=True)
    audio = audio.astype(np.float32)

    model_a, metadata = whisperx.load_align_model(
        language_code=LANG, device=DEVICE
    )

    # Format known transcript as a single segment spanning full audio
    duration = len(audio) / 16000
    segments = [{"text": spoken_text, "start": 0.0, "end": duration}]

    result = whisperx.align(
        segments, model_a, metadata, audio, device=DEVICE,
        return_char_alignments=False
    )
    return result  # result["segments"][i]["words"][j] → {"word", "start", "end", "score"}
```

> **Critical nuance:** When the spoken text is longer than ~30 seconds, WhisperX's internal
> VAD handles chunking automatically in the full pipeline, but when bypassing ASR and passing
> segments manually, split the transcript into sentence-sized segments first and pass them as
> separate entries in the `segments` list. This lets wav2vec2 align each sentence independently
> and avoids attention-span degradation on long sequences.

### Pattern 2: ASR-WER Guard

**What:** Run Whisper ASR on the generated audio, normalize both reference and hypothesis
with `EnglishTextNormalizer`, compute `jiwer.wer()`, and decide on regenerate vs. fallback.

**When to use:** After every alignment run as a mandatory fidelity check.

```python
# Source: pypi.org/project/jiwer + github.com/kurianbenoy/whisper_normalizer
from jiwer import wer
from whisper_normalizer.english import EnglishTextNormalizer
import whisper

_normalizer = EnglishTextNormalizer()

def compute_wer(reference_spoken: str, audio_path: str, model_size="base") -> float:
    """Returns 0.0–1.0; normalize both sides before comparing."""
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    hyp = result["text"]

    ref_norm = _normalizer(reference_spoken)
    hyp_norm = _normalizer(hyp)
    return wer(ref_norm, hyp_norm)

WER_THRESHOLD = 0.08  # ponytail: empirical; tighten to 0.05 if accent drift is a known issue

def check_wer(reference: str, audio_path: str) -> str:
    """Returns 'ok' | 'regenerate' | 'fallback'."""
    score = compute_wer(reference, audio_path)
    if score <= WER_THRESHOLD:
        return "ok", score
    # ponytail: one regenerate attempt before fallback
    return "regenerate", score
```

**Normalization is mandatory.** Without it, `"25%"` vs. `"twenty-five percent"` looks like 2
substitutions even when the TTS is correct. `EnglishTextNormalizer` handles numbers, titles,
contractions, and British spellings. Apply it to BOTH sides before calling `jiwer.wer()`.

### Pattern 3: Fallback — whisper-timestamped

**What:** When forced alignment fails (too many NaN-interpolated words, or WER exceeds
threshold after retry), use `whisper-timestamped` to derive word times via DTW.

**When to use:** ALIGN-04 trigger condition: `align_result` has > 20% words with
NaN/interpolated timestamps, OR WER check returns `"fallback"`.

```python
# Source: github.com/linto-ai/whisper-timestamped
import whisper_timestamped as wts

def fallback_align(wav_path: str, model_size="base") -> list[dict]:
    """Returns words[] in timeline.json format."""
    audio = wts.load_audio(wav_path)
    model = wts.load_model(model_size, device="cpu")
    result = wts.transcribe(model, audio, language="en",
                             vad="silero",
                             detect_disfluencies=True)
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({
                "w":       w["text"].strip(),
                "start":   round(w["start"], 3),
                "end":     round(w["end"],   3),
                "speaker": 1   # no speaker info in single-speaker fallback
            })
    return words
```

### Pattern 4: timeline.json Schema (Finalized)

Building on `PROJECT_PLAN.md §1`, adding `alignMethod` and `werScore` to `meta`, plus
`confidence` per-word for downstream quality filtering.

```jsonc
{
  "audio": {
    "path":        "out.wav",
    "sampleRate":  24000,
    "durationSec": 42.7
  },
  "words": [
    {
      "w":         "Hello",
      "start":     0.31,
      "end":       0.62,
      "speaker":   1,
      "confidence": 0.97   // optional; present when aligner returns a score
    }
  ],
  "sentences": [
    {
      "idx":       0,
      "text":      "Hello world, this is a test sentence.",
      "start":     0.31,
      "end":       3.90,
      "speaker":   1,
      "wordRange": [0, 8]   // half-open: words[0..8)
    }
  ],
  "scenes": [],             // populated by Phase 3; absent until then
  "meta": {
    "lang":         "en",
    "wer":          0.03,
    "generator":    "vibevoice-1.5B",
    "alignMethod":  "whisperx-forced",   // or "whisper-timestamped-fallback"
    "alignedAt":    "2026-07-08T12:00:00Z"
  }
}
```

**Sentence boundary derivation:** Split `spoken_text` into sentences with Python's built-in
`re.split(r'(?<=[.!?])\s+', text)` (no new dep). For each sentence, find the first and last
`words[]` index whose `.w` tokens match the sentence's tokens. `start = words[first].start`,
`end = words[last].end`, `wordRange = [first, last+1]`.

### Anti-Patterns to Avoid

- **Calling `whisperx.transcribe()` and then alignment:** Wasteful for this use case; we own the
  transcript. Skip straight to `whisperx.align()` with the known segment list.
- **Computing WER without normalizing:** Numbers, punctuation, and contractions will inflate WER
  and trigger false regenerations. Always normalize both sides.
- **Accumulating frame offsets with FPS multiplication:** Compute `round(start * fps)` per word
  independently; never accumulate frame counts across words (rounding drift).
- **Deriving `durationSec` from the transcript or word list:** Always read it from the actual
  audio file with `librosa.get_duration(path=wav_path)` after generation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Word-level timestamps | Custom CTC aligner | `whisperx.align()` | wav2vec2 phoneme alignment handles homophones, repeated words, accented speech; CTC from scratch is months of work |
| WER computation | Levenshtein distance in Python | `jiwer.wer()` | RapidFuzz C++ backend; handles multiple reference/hypothesis pairs; correct edit-distance semantics |
| Number normalization for WER | Regex-based num→word mapper | `EnglishTextNormalizer` | Already handles ordinals, currencies, dates, abbreviations; regex misses edge cases |
| Sentence splitting | NLP library (spaCy/NLTK) | `re.split(r'(?<=[.!?])\s+', text)` | We own the script; it's already clean; regex is sufficient |

---

## Common Pitfalls

### Pitfall 1: Numbers in the Spoken Text Break wav2vec2 Alignment

**What goes wrong:** Words containing digits (e.g. `"EM3985771"`, `"25%"`) are not in the
wav2vec2 vocabulary. WhisperX replaces them with wildcard tokens and then **interpolates**
their timestamps. Interpolated timestamps can be off by 2–3 seconds.

**Why it happens:** `WAV2VEC2_ASR_BASE_960H` was trained on LibriSpeech text that contains no
digit strings. The aligner substitutes `"*"` and guesses the timestamp position.

**How to avoid:** Phase 1's text normalizer (AUDIO-04) MUST expand all numbers to spoken words
before audio is generated AND before the spoken text is passed to `whisperx.align()`. Use
`EnglishTextNormalizer` to normalize the script. This is why Phase 1 must deliver both `raw`
and `spoken` forms.

**Warning signs:** `result["segments"][i]["words"][j]["score"]` is `NaN` or very low for
a cluster of words.

### Pitfall 2: WER Threshold Set Without Normalization

**What goes wrong:** Unnormalized WER of 0.10–0.15 triggers a regeneration loop even when the
TTS output is faithful. Every formatting difference (e.g. script says `"50%"`, ASR transcribes
`"fifty percent"`) counts as 2 errors.

**How to avoid:** Apply `EnglishTextNormalizer` to BOTH reference (spoken script) and
hypothesis (Whisper transcript) before calling `jiwer.wer()`. After normalization, a 0.08
threshold is realistic for Indian-accented TTS.

### Pitfall 3: Long Audio Segment Passed as One Segment

**What goes wrong:** Passing the full spoken text as a single segment to `whisperx.align()`
degrades alignment quality on audio longer than ~30 seconds. The wav2vec2 model's attention
span effectively covers ~30s chunks.

**How to avoid:** Split the spoken text into sentence-level entries in the `segments` list
before calling `align()`. Each entry should be one or a few sentences. Set `start` and `end`
to the approximate sentence boundary (use VAD if available, or uniform time estimates; the
aligner will refine them).

### Pitfall 4: Fallback Doesn't Match Primary Schema

**What goes wrong:** `whisper-timestamped` output uses `{"text": "word", "start": 0.3,
"end": 0.6}` per word, while the primary path uses `{"w": "word", "start": 0.3, "end": 0.6,
"speaker": 1}`. Passing raw fallback output to `schema.py` crashes or emits malformed JSON.

**How to avoid:** `fallback.py` MUST normalize output into the exact `words[]` dict shape
(field name `"w"`, speaker defaulting to 1) before returning. The `schema.py` builder must
accept only the normalized shape — never handle both formats.

### Pitfall 5: `durationSec` Derived from Word Timestamps

**What goes wrong:** `words[-1].end` is slightly shorter than the true audio duration (silence
at the end is not spoken text). Remotion then clips the last visual scene.

**How to avoid:** Always compute `durationSec = librosa.get_duration(path=wav_path)` from the
actual audio file. Never derive it from alignment output.

### Pitfall 6: Indian Accent Inflates WER on Verification Pass

**What goes wrong:** The ASR model used for WER verification (standard Whisper) itself has
higher WER on Indian-accented speech (+5–10% relative to neutral English). A faithful TTS
output may still fail the WER gate because the verification ASR is worse at understanding it.

**How to avoid:** Use `whisper large-v2` or `whisper turbo` for verification (better accent
robustness than `base`). Consider raising the threshold to 0.10 specifically for Indian voice
profiles. Log the WER so it can be tuned post-hoc.

---

## Code Examples

### Loading Audio at 16kHz (WhisperX requirement)

```python
# Source: WhisperX README — audio must be 16kHz float32 mono
import librosa, numpy as np

def load_16k(wav_path: str) -> np.ndarray:
    audio, _ = librosa.load(wav_path, sr=16000, mono=True)
    return audio.astype(np.float32)
```

### NaN Timestamp Detection (trigger fallback)

```python
# ponytail: simple count; switch to per-word check if precision matters
import math

def nan_ratio(words: list[dict]) -> float:
    nan_count = sum(1 for w in words if w.get("start") is None or
                    (isinstance(w.get("start"), float) and math.isnan(w["start"])))
    return nan_count / max(len(words), 1)

FALLBACK_NAN_THRESHOLD = 0.20   # >20% NaN words → switch to whisper-timestamped
```

### Sentence Boundary Derivation (no deps)

```python
import re

def split_sentences(spoken_text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', spoken_text) if s.strip()]

def map_words_to_sentences(words: list[dict], sentences: list[str]) -> list[dict]:
    """Returns sentences[] with start/end/wordRange populated."""
    result = []
    w_idx = 0
    for s_idx, sent in enumerate(sentences):
        tokens = sent.split()
        first = w_idx
        last  = min(w_idx + len(tokens) - 1, len(words) - 1)
        result.append({
            "idx":       s_idx,
            "text":      sent,
            "start":     words[first]["start"],
            "end":       words[last]["end"],
            "speaker":   words[first].get("speaker", 1),
            "wordRange": [first, last + 1]
        })
        w_idx = last + 1
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vanilla Whisper segment timestamps (~1s accuracy) | WhisperX wav2vec2 forced alignment (<100ms) | 2023 (Interspeech) | Word captions and scene sync are now reliable |
| Separate Whisper + forced aligner install | `pip install whisperx` (all-in-one) | 2023–2024 | Simpler Colab setup |
| Alignment requires running ASR first | `whisperx.align()` accepts known segments | 2024 (issue #649) | Can skip ASR entirely when transcript is known |
| Custom WER scripts | `jiwer 4.0.0` with composable transforms | 2025 | RapidFuzz backend; handles empty strings |
| Manual text normalization for WER | `whisper-normalizer` EnglishTextNormalizer | 2022 (OpenAI paper) | Numbers, contractions, titles handled correctly |

**Deprecated/outdated:**
- Whisper `transcribe()` + manual timestamp extraction: Replaced by WhisperX for any word-level use case.
- Pure regex WER scripts: jiwer is faster, more correct, and handles multi-sentence inputs cleanly.

---

## Open Questions

1. **Multi-speaker attribution from VibeVoice**
   - What we know: VibeVoice supports up to 4 speakers; the audio output is a single mixed WAV.
   - What's unclear: Does VibeVoice output per-speaker segments or interleaved speech? If
     speakers overlap, WhisperX diarization (pyannote 3.1) is needed. If speakers are sequential,
     we can infer speaker from sentence boundaries.
   - Recommendation: Defer to Phase 1 — Phase 1 must specify whether multi-speaker output is
     per-segment or interleaved. If interleaved, add pyannote diarization step in Phase 2.

2. **WER threshold for Indian voice profiles**
   - What we know: Indian-accented speech adds ~5–10% WER on standard Whisper. Forced alignment
     is phoneme-based so less affected than ASR, but the WER guard uses ASR.
   - What's unclear: Whether `large-v2` (better accent coverage) is available on free Colab
     within the daily GPU cap for the verification pass.
   - Recommendation: Start with `whisper base` for speed; log WER per generation; adjust threshold
     empirically after 5-10 test generations with the target voice.

3. **Exact behavior when `spoken_text` and generated audio diverge structurally**
   - What we know: VibeVoice may skip low-confidence tokens or add filler words.
   - What's unclear: Whether WhisperX alignment gracefully handles a transcript that has more
     words than what was spoken (e.g., TTS skipped a phrase).
   - Recommendation: If WER guard passes but `nan_ratio > threshold`, the fallback is already
     the right behaviour. Document the policy: WER check catches semantic drift; nan_ratio catches
     structural alignment failure.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (standard; no config file yet — see Wave 0) |
| Config file | `tests/conftest.py` (Wave 0 gap) |
| Quick run command | `pytest align/tests/ -x -q` |
| Full suite command | `pytest align/tests/ -v` |
| Estimated runtime | ~30 seconds (CPU, `whisper base`, short clip) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALIGN-01 | `align_known_transcript("test.wav", spoken_text)` returns `words[]` with non-NaN start/end for each word | unit | `pytest align/tests/test_aligner.py::test_words_have_timestamps -x` | ❌ Wave 0 gap |
| ALIGN-01 | Words timestamps are monotonically increasing | unit | `pytest align/tests/test_aligner.py::test_word_timestamps_monotonic -x` | ❌ Wave 0 gap |
| ALIGN-02 | `compute_wer(reference, audio)` returns < 0.08 on a known-good clip | unit | `pytest align/tests/test_verifier.py::test_wer_known_good -x` | ❌ Wave 0 gap |
| ALIGN-02 | `compute_wer(reference, audio)` returns > 0.08 on a deliberately drifted clip | unit | `pytest align/tests/test_verifier.py::test_wer_drift_detected -x` | ❌ Wave 0 gap |
| ALIGN-03 | `timeline.json` passes JSON schema validation (all required fields present) | unit | `pytest align/tests/test_schema.py::test_timeline_schema_valid -x` | ❌ Wave 0 gap |
| ALIGN-03 | `sentences[].wordRange` is contiguous and covers all words | unit | `pytest align/tests/test_schema.py::test_word_range_covers_all -x` | ❌ Wave 0 gap |
| ALIGN-04 | Fallback `fallback_align()` returns same `words[]` shape as primary path | unit | `pytest align/tests/test_aligner.py::test_fallback_schema_matches_primary -x` | ❌ Wave 0 gap |

### Nyquist Sampling Rate

- **Minimum sample interval:** After every committed task → run: `pytest align/tests/ -x -q`
- **Full suite trigger:** Before merging final task of the alignment plan wave
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~30 seconds

### Wave 0 Gaps (must be created before implementation)

- [ ] `align/tests/conftest.py` — shared 2-second test WAV fixture + known spoken text
- [ ] `align/tests/test_aligner.py` — covers ALIGN-01, ALIGN-04
- [ ] `align/tests/test_verifier.py` — covers ALIGN-02 (known-good + drifted clips)
- [ ] `align/tests/test_schema.py` — covers ALIGN-03 (schema validation, word range coverage)
- [ ] `pytest` install: `pip install pytest` if not present in Colab env

---

## Sources

### Primary (HIGH confidence)
- [github.com/m-bain/whisperX](https://github.com/m-bain/whisperX) — README, issue #649 (known-transcript alignment pattern), alignment.py `DEFAULT_ALIGN_MODELS_TORCH`
- [pypi.org/project/whisperx/](https://pypi.org/project/whisperx/) — v3.8.6, Python >=3.10 <3.14, CUDA 12.8, May 2026
- [pypi.org/project/jiwer/](https://pypi.org/project/jiwer/) — v4.0.0, Jun 2025, empty-string behavior
- [jitsi.github.io/jiwer](https://jitsi.github.io/jiwer/) — `Compose`, `wer_standardize` preset, transformation classes
- [github.com/linto-ai/whisper-timestamped](https://github.com/linto-ai/whisper-timestamped) — v1.15.9, output schema, VAD modes, known limitations
- [kurianbenoy.github.io/whisper_normalizer](https://kurianbenoy.github.io/whisper_normalizer/) — `EnglishTextNormalizer`, `BasicTextNormalizer` APIs

### Secondary (MEDIUM confidence)
- [docs.pytorch.org/audio WAV2VEC2_ASR_BASE_960H](https://docs.pytorch.org/audio/2.4.0/generated/torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.html) — MIT license, pre-trained on LibriSpeech 960h
- [arxiv.org/abs/2303.00747](https://arxiv.org/abs/2303.00747) — WhisperX Interspeech 2023 paper; 93.2% word-timing precision on telephone speech
- [deepwiki.com/m-bain/whisperX/3.3-forced-alignment-system](https://deepwiki.com/m-bain/whisperX/3.3-forced-alignment-system) — interpolate_nans behavior, wildcard character handling
- [github.com/m-bain/whisperX/issues/1298](https://github.com/m-bain/whisperX/issues/1298) — number timestamp errors (up to 2.95s drift)

### Tertiary (LOW confidence — needs validation)
- Indian accent +5–10% WER claim: from [novascribe.ai/how-accurate-is-whisper](https://novascribe.ai/how-accurate-is-whisper); cited as ballpark only — measure empirically with target voice
- WER threshold of 0.08: derived from community norms for TTS verification; not from an official source — tune after 5–10 test runs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — version-verified on PyPI; Python/CUDA requirements confirmed
- Architecture: HIGH — known-transcript alignment pattern verified via issue #649; WER pattern verified via jiwer + whisper-normalizer docs
- Pitfalls: HIGH (numbers, normalization, durationSec); MEDIUM (Indian accent WER, long-audio segment limit)
- WER threshold: LOW — empirical starting point only; must be validated with target voice

**Research date:** 2026-07-08
**Valid until:** 2026-08-08 (30 days; fast-moving — re-check whisperx version before execution)
