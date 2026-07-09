"""Tests for tts.schema — inter-phase timeline.json contract.

Phase 2 (alignment engine) imports Timeline from tts.schema. These tests
define the exact shape of the timeline.json contract.
"""
import io
import json
import struct
import pytest


def _make_wav_bytes(duration_sec: float = 2.0, sample_rate: int = 24000) -> bytes:
    """Build a valid PCM16 WAV in memory using stdlib only."""
    n_samples = int(sample_rate * duration_sec)
    data_size = n_samples * 2  # PCM16 = 2 bytes/sample
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)
    return buf.getvalue()


def test_timeline_validates(tmp_path):
    """Timeline.model_validate() succeeds for a valid minimal payload."""
    from tts.schema import Timeline
    t = Timeline.model_validate({
        "audio": {"path": "x.wav", "sampleRate": 24000, "durationSec": 1.0},
        "meta": {"generator": "vibevoice-0.5B"},
    })
    assert t.audio.path == "x.wav"
    assert t.audio.sampleRate == 24000
    assert t.audio.durationSec == 1.0
    assert t.words == []
    assert t.sentences == []
    assert t.scenes == []
    assert t.meta.generator == "vibevoice-0.5B"
    assert t.meta.lang == "en"
    assert t.meta.wer is None
    assert t.meta.alignMethod is None


def test_write_phase1_timeline_structure(tmp_path):
    """write_phase1_timeline() produces JSON with keys: audio, words, sentences, scenes, meta.

    words=[], sentences=[], scenes=[] in Phase 1 output (populated in Phase 2+).
    meta['generator'] matches the generator argument.
    audio['durationSec'] reflects actual file duration (derived via soundfile).
    """
    from tts.schema import write_phase1_timeline

    wav_path = str(tmp_path / "test.wav")
    out_path = str(tmp_path / "timeline.json")

    with open(wav_path, "wb") as f:
        f.write(_make_wav_bytes(duration_sec=2.0))

    write_phase1_timeline(wav_path, "vibevoice-test", out_path)

    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)

    assert set(data.keys()) >= {"audio", "words", "sentences", "scenes", "meta"}
    assert data["words"] == []
    assert data["sentences"] == []
    assert data["scenes"] == []
    assert data["meta"]["generator"] == "vibevoice-test"
    assert data["meta"]["wer"] is None
    assert data["meta"]["alignMethod"] is None
    assert data["audio"]["path"] == wav_path
    assert data["audio"]["durationSec"] == pytest.approx(2.0, abs=0.05)
