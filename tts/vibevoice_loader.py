"""tts/vibevoice_loader.py — lazy VibeVoice model loader (tracked in-repo).

Replaces the old import of VibeVoice/app.py: that file lives in the gitignored
upstream clone, so it never survives a fresh `git clone` on Colab.

Model selection via env VIBEVOICE_MODEL:
  "0.5B"  (default) — microsoft streaming model. Fixed .pt cached-prompt voices.
  "1.5B"            — community fork. TRUE voice cloning from a reference WAV.
  "Large"           — ~7B-class model. Needs ~20GB VRAM (Colab Pro A100/L4);
                      does NOT fit the free T4.

For 1.5B/Large the notebook must clone+install vibevoice-community/VibeVoice
(Microsoft removed the non-streaming TTS code from their repo).
MODEL_PATH env overrides the HF repo id for any size.
"""
import logging
import os

MODEL_SIZE = os.environ.get("VIBEVOICE_MODEL", "0.5B")
_DEFAULT_PATHS = {
    "0.5B": "microsoft/VibeVoice-Realtime-0.5B",
    "1.5B": "vibevoice/VibeVoice-1.5B",
    "Large": "aoi-ot/VibeVoice-Large",  # ~9B params, the "7B" model — mirror of removed microsoft/VibeVoice-Large
}
MODEL_PATH = os.environ.get("MODEL_PATH", _DEFAULT_PATHS.get(MODEL_SIZE, _DEFAULT_PATHS["0.5B"]))
SAMPLE_RATE = 24000

_model = None
_processor = None
_device = None

log = logging.getLogger(__name__)


def is_streaming() -> bool:
    """True for the 0.5B cached-prompt streaming model."""
    return MODEL_SIZE == "0.5B"


def load():
    """Lazy-load model + processor once. Returns (model, processor, device)."""
    global _model, _processor, _device
    if _model is not None:
        return _model, _processor, _device

    import torch

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    # bf16 on CPU too: halves RAM vs float32 — free Colab has ~12.7GB and the
    # kernel OOM-kills a float32 1.5B load ("^C" at Loading checkpoint shards)
    dtype = torch.bfloat16
    if _device == "cpu":
        log.warning(
            "No GPU detected — model %s will load on CPU (slow, may exhaust RAM). "
            "On Colab: Runtime -> Change runtime type -> T4 GPU.", MODEL_SIZE,
        )
    log.info("Loading %s (%s) on %s (first call is slow)", MODEL_PATH, MODEL_SIZE, _device)

    if is_streaming():
        from vibevoice.modular.modeling_vibevoice_streaming_inference import (
            VibeVoiceStreamingForConditionalGenerationInference as _Model,
        )
        from vibevoice.processor.vibevoice_streaming_processor import (
            VibeVoiceStreamingProcessor as _Processor,
        )
        ddpm_steps = 5
    else:
        from vibevoice.modular.modeling_vibevoice_inference import (
            VibeVoiceForConditionalGenerationInference as _Model,
        )
        from vibevoice.processor.vibevoice_processor import (
            VibeVoiceProcessor as _Processor,
        )
        ddpm_steps = 10

    _processor = _Processor.from_pretrained(MODEL_PATH)
    # low_cpu_mem_usage: stream shards instead of double-allocating in RAM
    try:
        _model = _Model.from_pretrained(
            MODEL_PATH, torch_dtype=dtype, device_map=_device,
            low_cpu_mem_usage=True,
            attn_implementation="flash_attention_2" if _device == "cuda" else "sdpa",
        )
    except Exception:
        # flash-attn not installed — sdpa works everywhere
        _model = _Model.from_pretrained(
            MODEL_PATH, torch_dtype=dtype, device_map=_device,
            low_cpu_mem_usage=True,
            attn_implementation="sdpa",
        )
    _model.eval()
    _model.set_ddpm_inference_steps(num_steps=ddpm_steps)
    return _model, _processor, _device
