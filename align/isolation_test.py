"""
align/isolation_test.py — Phase 2 isolation gate (run on Colab GPU only).

PURPOSE:
  Verifies the full alignment pipeline end-to-end on a real audio clip before
  Phase 4 begins. This script is the mandatory gate artifact.

REQUIREMENTS:
  - Run on Colab GPU (whisperx + whisper_timestamped require CUDA)
  - Set env var: TEST_CLIP_PATH = path to a 5-30s English speech WAV
  - Spoken text below MUST match the content of your clip

COLAB COMMANDS (copy-paste in order):
  !pip install whisperx jiwer whisper-normalizer whisper-timestamped librosa soundfile pydantic
  !export TEST_CLIP_PATH="/path/to/your/clip.wav"
  !python align/isolation_test.py

EXIT CODES:
  0 — both tests passed
  1 — one or more assertions failed

EXPECTED RESULTS (Phase 4 gate criteria):
  Known-good: alignMethod="whisperx-forced", wer < 0.08
  Fallback:   alignMethod="whisper-timestamped-fallback", schema keys = {w, start, end, speaker}
"""
import os
import sys
import json

# ── configuration ──────────────────────────────────────────────────────────────

WAV_PATH = os.environ.get("TEST_CLIP_PATH", "")

# UPDATE THIS TEXT to match the exact content of your test clip (no digits).
# The default is a generic sentence — you should replace it with the actual spoken text.
SPOKEN_TEXT = (
    "Hello world. This is a test sentence for the alignment engine. "
    "Forced alignment produces word level timestamps."
)

OUTPUT_KNOWN_GOOD = "/tmp/timeline_known_good.json"
OUTPUT_FALLBACK   = "/tmp/timeline_fallback.json"

# ── execution ──────────────────────────────────────────────────────────────────

def main():
    if not WAV_PATH:
        print("ERROR: TEST_CLIP_PATH env var not set. Set it to a 5-30s English speech WAV.")
        print("  export TEST_CLIP_PATH='/path/to/clip.wav'")
        sys.exit(1)

    if not os.path.exists(WAV_PATH):
        print(f"ERROR: TEST_CLIP_PATH={WAV_PATH!r} does not exist.")
        sys.exit(1)

    # ── test 1: known-good clip (primary path) ─────────────────────────────────────

    print("=" * 60)
    print("ISOLATION TEST 1: KNOWN-GOOD CLIP (primary path)")
    print("=" * 60)

    from align.align_pipeline import run_alignment, AlignmentDriftError

    try:
        tl = run_alignment(WAV_PATH, SPOKEN_TEXT, output_path=OUTPUT_KNOWN_GOOD)
    except AlignmentDriftError as e:
        print(f"WARN: AlignmentDriftError raised (WER={e.wer_score:.3f}). Retrying with fallback.")
        tl = run_alignment(WAV_PATH, SPOKEN_TEXT, output_path=OUTPUT_KNOWN_GOOD, use_fallback=True)

    print(f"WER:          {tl['meta']['wer']}")
    print(f"alignMethod:  {tl['meta']['alignMethod']}")
    print(f"durationSec:  {tl['audio']['durationSec']}")
    print(f"Word count:   {len(tl['words'])}")
    print(f"Sentence cnt: {len(tl['sentences'])}")
    print("First 3 words:")
    for w in tl["words"][:3]:
        print(f"  {w}")

    # Assertions
    assert tl["meta"]["alignMethod"] == "whisperx-forced", (
        f"Expected whisperx-forced, got {tl['meta']['alignMethod']!r}"
    )
    assert tl["meta"]["wer"] < 0.08, (
        f"WER {tl['meta']['wer']:.4f} exceeds threshold 0.08 — clip may be mismatched"
    )
    assert tl["audio"]["durationSec"] > tl["words"][-1]["end"], (
        "durationSec must exceed last word end (trailing silence)"
    )
    assert {"audio", "words", "sentences", "meta"}.issubset(tl.keys())
    print("KNOWN-GOOD: PASS")

    # ── test 2: fallback path ──────────────────────────────────────────────────────

    print()
    print("=" * 60)
    print("ISOLATION TEST 2: FALLBACK PATH (whisper-timestamped)")
    print("=" * 60)

    tl_fb = run_alignment(
        WAV_PATH, "Hello world. This is a test.",
        output_path=OUTPUT_FALLBACK,
        use_fallback=True,
    )

    print(f"alignMethod:  {tl_fb['meta']['alignMethod']}")
    print(f"Word count:   {len(tl_fb['words'])}")
    print("First 3 words:")
    for w in tl_fb["words"][:3]:
        print(f"  {w}")

    # Assertions
    assert tl_fb["meta"]["alignMethod"] == "whisper-timestamped-fallback", (
        f"Expected whisper-timestamped-fallback, got {tl_fb['meta']['alignMethod']!r}"
    )
    required_keys = {"w", "start", "end", "speaker"}
    for w in tl_fb["words"]:
        assert required_keys.issubset(w.keys()), f"Missing keys: {required_keys - w.keys()}"
    print("FALLBACK: PASS")

    # ── summary ────────────────────────────────────────────────────────────────────

    print()
    print("=" * 60)
    print("PHASE 2 ISOLATION GATE: PASSED")
    print(f"Known-good WER:  {tl['meta']['wer']:.4f} (threshold 0.08)")
    print(f"Fallback method: {tl_fb['meta']['alignMethod']}")
    print(f"Outputs written: {OUTPUT_KNOWN_GOOD}, {OUTPUT_FALLBACK}")
    print("Phase 4 may begin.")
    print("=" * 60)


if __name__ == "__main__":
    main()
