"""tts/vibevoice_loader.py — lazy VibeVoice 0.5B model loader (tracked in-repo).

Replaces the old import of VibeVoice/app.py: that file lives in the gitignored
upstream clone, so it never survives a fresh `git clone` on Colab.

Requires the upstream package to be installed: `pip install -e VibeVoice`
(done by colab_pipeline.ipynb cell 1). GPU is used when available.
"""
import logging
import os

MODEL_PATH = os.environ.get("MODEL_PATH", "microsoft/VibeVoice-Realtime-0.5B")
SAMPLE_RATE = 24000

_model = None
_processor = None
_device = None

log = logging.getLogger(__name__)


def load():
    """Lazy-load model + processor once. Returns (model, processor, device)."""
    global _model, _processor, _device
    if _model is not None:
        return _model, _processor, _device

    import torch
    from vibevoice.modular.modeling_vibevoice_streaming_inference import (
        VibeVoiceStreamingForConditionalGenerationInference,
    )
    from vibevoice.processor.vibevoice_streaming_processor import (
        VibeVoiceStreamingProcessor,
    )

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if _device == "cuda" else torch.float32
    log.info("Loading %s on %s (first call is slow)", MODEL_PATH, _device)

    _processor = VibeVoiceStreamingProcessor.from_pretrained(MODEL_PATH)
    try:
        _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            MODEL_PATH, torch_dtype=dtype, device_map=_device,
            attn_implementation="flash_attention_2" if _device == "cuda" else "sdpa",
        )
    except Exception:
        # flash-attn not installed — sdpa works everywhere
        _model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
            MODEL_PATH, torch_dtype=dtype, device_map=_device,
            attn_implementation="sdpa",
        )
    _model.eval()
    _model.set_ddpm_inference_steps(num_steps=5)
    return _model, _processor, _device
