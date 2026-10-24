"""
Tests for Voice Service (STT, TTS, WakeWord, EchoGate, API)
"""
import io
import os
import sys
import wave
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

# Ensure services/voice-service root is in sys.path
VOICE_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(VOICE_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_SERVICE_ROOT))

from stt import SpeechToText
from tts import TextToSpeech
from wake_word import WakeWordDetector
from echo_gate import EchoGate
from server import app


@pytest.fixture
def sample_wav_bytes():
    """Generates 0.5s 16kHz sine wave audio bytes."""
    sample_rate = 16000
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = (0.1 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    buf.seek(0)
    return buf.getvalue()


def test_echo_gate():
    gate = EchoGate(post_playback_delay_ms=50)
    assert not gate.is_mic_muted
    gate.on_tts_start()
    assert gate.is_mic_muted
    gate.on_tts_end()
    assert not gate.is_mic_muted


def test_wake_word_detector():
    detector = WakeWordDetector(wake_words=["hey_jarvis"], sensitivity=0.5)
    # Empty or zero audio shouldn't trigger error
    silence = np.zeros(1280, dtype=np.int16)
    res = detector.process_frame(silence)
    assert res is None or isinstance(res, tuple)


def test_tts_synthesis(tmp_path):
    tts = TextToSpeech()
    out_file = tmp_path / "test_speech.wav"
    success = tts.synthesize("Hello world, J.A.R.V.I.S online.", out_file)
    assert success is True
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    # Test byte synthesis
    data = tts.synthesize_bytes("Testing voice synthesis bytes.")
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_stt_transcribe_pcm(sample_wav_bytes):
    stt = SpeechToText()
    # Should not crash on valid audio buffer
    raw_pcm = sample_wav_bytes[44:]  # strip WAV header
    result = stt.transcribe_pcm(raw_pcm)
    assert isinstance(result, str)


def test_voice_server_endpoints(sample_wav_bytes):
    client = TestClient(app)
    
    # Health endpoint
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "jarvis-voice-service"

    # Synthesize endpoint
    synth_res = client.post("/v1/voice/synthesize", json={"text": "Voice service test"})
    assert synth_res.status_code == 200
    assert synth_res.headers["content-type"] == "audio/wav"
    assert len(synth_res.content) > 0

    # Transcribe endpoint
    files = {"file": ("test.wav", sample_wav_bytes, "audio/wav")}
    trans_res = client.post("/v1/voice/transcribe", files=files)
    assert trans_res.status_code == 200
    assert "text" in trans_res.json()
