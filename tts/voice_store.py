"""Voice registry for the TTS service.

Abstracts .pt cached-prompt voices (0.5B) and raw .wav reference audio.

AUDIO-05 persistence: voices/default_indian.wav should be committed to the
repo so it survives git clone.  If missing, falls back to in-Samuel_man.pt
(0.5B).  For arbitrary voice cloning from raw audio, upgrade to
vibevoice-community/VibeVoice 1.5B fork.

The voices/ directory is kept with a .gitkeep so it exists after git clone
even before any .wav is committed.
"""
import glob
import shutil
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_VOICES_DIR = _REPO_ROOT / "VibeVoice" / "demo" / "voices" / "streaming_model"
_UPLOAD_DIR = _REPO_ROOT / "voices"

# In-memory registry: voice_id -> absolute path string
_registry: dict[str, str] = {}


def _build_registry() -> None:
    """Populate registry from .pt files + default_indian.wav fallback."""
    # Scan all .pt files (0.5B cached prompts)
    for pt in sorted(_VOICES_DIR.glob("**/*.pt")):
        _registry[pt.stem] = str(pt.resolve())

    # Register default Indian voice
    wav_path = _UPLOAD_DIR / "default_indian.wav"
    pt_path = _VOICES_DIR / "in-Samuel_man.pt"
    if wav_path.exists():
        _registry["default"] = str(wav_path.resolve())
    elif pt_path.exists():
        _registry["default"] = str(pt_path.resolve())
    # else: no default registered — get_voice_path("default") raises KeyError


_build_registry()


def get_voice_path(speaker_id: str) -> str:
    """Return path for speaker_id; raises KeyError if not registered."""
    return _registry[speaker_id]


def list_voice_ids() -> list[str]:
    """Return all registered voice IDs, 'default' first if present."""
    ids = list(_registry.keys())
    if "default" in ids:
        ids.remove("default")
        return ["default"] + ids
    return ids


def register_voice(voice_id: str, file_path: str) -> None:
    """Add voice_id -> file_path to the registry (in-memory + disk copy under voices/)."""
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = _UPLOAD_DIR / (voice_id + Path(file_path).suffix)
    if str(Path(file_path).resolve()) != str(dest.resolve()):
        shutil.copy2(file_path, dest)
    _registry[voice_id] = str(dest.resolve())
