# ponytail: AUDIO-03 via 0.5B stores reference audio only; true voice conditioning needs the 1.5B fork (upgrade path: vibevoice-community/VibeVoice)
"""FastAPI TTS HTTP service.

Endpoints (permanent contract — backend is swappable via ENDPOINT_URL):
  POST /synthesize   {text, speaker_id, cfg_scale} -> audio/wav 24kHz PCM16
  GET  /voices       -> ["default", "in-Samuel_man", ...]
  POST /clone        multipart {voice_id, reference} -> {"voice_id", "message"}

Auth: Bearer token via API_SECRET env var (default: "dev-secret").
VibeVoice model is lazy-loaded inside run_vibevoice() — server imports and
TestClient usage on Windows work without a GPU or the vibevoice package.
"""
import io
import logging
import os
import shutil
import tempfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

import tts.voice_store as voice_store

log = logging.getLogger(__name__)

app = FastAPI(title="VibeVoice TTS Service")
_bearer = HTTPBearer()

API_SECRET = os.environ.get("API_SECRET", "dev-secret")


def _get_api_secret() -> str:
    """Read at call time so tests can monkeypatch the env var."""
    return os.environ.get("API_SECRET", "dev-secret")


def _check_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if creds.credentials != _get_api_secret():
        raise HTTPException(status_code=401, detail="Invalid token")


def run_vibevoice(text: str, speaker_id: str, cfg_scale: float = 1.5):
    """Generate audio via VibeVoice 0.5B. Lazy-loaded — not called on import.

    Returns np.ndarray float32 at 24kHz.
    Raises KeyError if speaker_id not found.
    """
    import copy
    import torch
    import numpy as np

    voice_path = voice_store.get_voice_path(speaker_id)

    # Lazy-load model (mirrors VibeVoice/app.py _load_local pattern)
    from VibeVoice.app import _load_local, _processor, _model  # type: ignore
    _load_local()

    if voice_path.endswith(".pt"):
        cached = torch.load(voice_path, map_location="cpu", weights_only=False)
    else:
        # Raw wav — 0.5B cannot truly condition on arbitrary audio;
        # fall back to default .pt voice and log a warning.
        log.warning(
            "AUDIO-03: 0.5B model cannot condition on raw WAV %s; "
            "using in-Samuel_man.pt. Upgrade to 1.5B fork for true cloning.",
            voice_path,
        )
        from VibeVoice.app import VOICES  # type: ignore
        cached = torch.load(VOICES["in-Samuel_man"], map_location="cpu", weights_only=False)

    from VibeVoice.app import _processor as proc, _model as mdl  # type: ignore
    inputs = proc.process_input_with_cached_prompt(
        text=text, cached_prompt=cached, padding=True,
        return_tensors="pt", return_attention_mask=True,
    )
    outputs = mdl.generate(
        **inputs, max_new_tokens=None, cfg_scale=cfg_scale,
        tokenizer=proc.tokenizer, generation_config={"do_sample": False},
        verbose=False, all_prefilled_outputs=copy.deepcopy(cached),
    )
    audio = outputs.speech_outputs[0]
    if audio is None:
        raise RuntimeError("No audio generated (input may be too short).")
    return audio.float().cpu().numpy().reshape(-1)


class SynthesizeRequest(BaseModel):
    text: str
    speaker_id: str = "default"
    cfg_scale: float = 1.5


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest, _: None = Depends(_check_auth)) -> Response:
    words = req.text.split()
    if len(words) < 3:
        raise HTTPException(status_code=400, detail=f"Input too short ({len(words)} words)")

    audio_np = run_vibevoice(req.text, req.speaker_id, req.cfg_scale)

    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, audio_np, 24000, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return Response(content=buf.read(), media_type="audio/wav")


@app.get("/voices")
def list_voices() -> list[str]:
    return voice_store.list_voice_ids()


@app.post("/clone")
def clone_voice(
    voice_id: str = Form(...),
    reference: UploadFile = File(...),
    _: None = Depends(_check_auth),
) -> dict:
    if voice_id in voice_store.list_voice_ids():
        raise HTTPException(status_code=400, detail="voice_id already exists")

    # Save upload to a temp file then register
    suffix = os.path.splitext(reference.filename or ".wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(reference.file, tmp)
        tmp_path = tmp.name

    log.warning(
        "AUDIO-03: POST /clone stores reference audio for voice_id=%s. "
        "The 0.5B model uses pre-computed .pt prompts for synthesis; "
        "upgrade to 1.5B fork for true voice cloning from arbitrary audio.",
        voice_id,
    )
    voice_store.register_voice(voice_id, tmp_path)
    os.unlink(tmp_path)
    return {"voice_id": voice_id, "message": "registered"}
