"""
backend/audio/omnivoice_tts.py
OmniVoice 24kHz Zero-Shot Voice Cloning TTS with Throttled Amplitude Streaming (25 Hz).
Includes automatic Edge-TTS (en-GB-RyanNeural) CPU fallback and reference WAV auto-generator.
"""

import asyncio
import io
import math
import os
import time
import logging
from pathlib import Path
from typing import Optional, Callable, List, AsyncGenerator, Any
import numpy as np
import sounddevice as sd
import soundfile as sf
import edge_tts
from backend.config import settings

logger = logging.getLogger("jarvis.audio.tts")

class OmniVoiceTTS:
    """Zero-shot voice cloning and British J.A.R.V.I.S speech synthesis."""

    def __init__(self):
        self.ref_audio_path = settings.JARVIS_REF_WAV
        self.device = settings.OMNIVOICE_DEVICE
        self.voice_name = settings.VOICE_NAME
        self.is_speaking: bool = False
        self._stop_requested: bool = False
        self._omnivoice_model = None
        self._amplitude_listeners: List[Callable[[float, str], Any]] = []

        # Ensure reference audio directory exists
        self.ref_audio_path.parent.mkdir(parents=True, exist_ok=True)

    def add_amplitude_listener(self, cb: Callable[[float, str], Any]) -> None:
        self._amplitude_listeners.append(cb)

    def _emit_state(self, amplitude: float, state: str) -> None:
        for cb in self._amplitude_listeners:
            try:
                cb(amplitude, state)
            except Exception:
                pass

    async def ensure_reference_audio(self) -> None:
        """Generates 6-second British reference WAV if not present."""
        if not self.ref_audio_path.exists():
            logger.info(f"[OmniVoiceTTS] Generating reference audio: {self.ref_audio_path}")
            ref_text = "Good day, Sir. All core systems are calibrated, operational, and awaiting your command."
            communicate = edge_tts.Communicate(ref_text, self.voice_name)
            mp3_bytes = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes.write(chunk["data"])
            mp3_bytes.seek(0)

            # Convert to 24kHz WAV via soundfile
            try:
                data, sr = sf.read(mp3_bytes)
                sf.write(str(self.ref_audio_path), data, sr, format='WAV', subtype='PCM_16')
                logger.info(f"[OmniVoiceTTS] Successfully saved reference audio to {self.ref_audio_path}")
            except Exception as e:
                logger.warning(f"[OmniVoiceTTS] Could not transcode reference WAV: {e}")

    def load_omnivoice_if_available(self) -> bool:
        """Attempts to load OmniVoice model on GPU."""
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            if self._omnivoice_model is not None:
                return True

            from omnivoice.models.omnivoice import OmniVoice
            logger.info("[OmniVoiceTTS] Loading OmniVoice model onto CUDA...")
            self._omnivoice_model = OmniVoice.from_pretrained(
                settings.OMNIVOICE_MODEL_ID,
                device_map=self.device,
                dtype=torch.float16
            )
            logger.info("[OmniVoiceTTS] OmniVoice loaded successfully.")
            return True
        except Exception as e:
            logger.debug(f"[OmniVoiceTTS] OmniVoice CUDA initialization bypassed ({e}); using Edge-TTS.")
            return False

    async def speak(self, text: str) -> None:
        """
        Synthesizes speech and streams audio playback with throttled RMS amplitude (25 Hz).
        Supports instant interruption (barge-in).
        """
        if not text or not text.strip():
            return

        self._stop_requested = False
        self.is_speaking = True
        self._emit_state(0.1, "SPEAKING")

        await self.ensure_reference_audio()

        # Try OmniVoice CUDA if available
        if self.load_omnivoice_if_available():
            try:
                await self._speak_omnivoice(text)
                self.is_speaking = False
                self._emit_state(0.0, "IDLE")
                return
            except Exception as e:
                logger.warning(f"[OmniVoice] Synthesis failed: {e}. Falling back to Edge-TTS.")

        # High-fidelity Edge-TTS Fallback
        await self._speak_edge_tts(text)
        self.is_speaking = False
        self._emit_state(0.0, "IDLE")

    async def _speak_omnivoice(self, text: str) -> None:
        import torch
        logger.info(f"[OmniVoice] Synthesizing zero-shot cloned voice for: '{text[:40]}...'")
        audio_tensor = self._omnivoice_model.generate(
            text=text,
            ref_audio=str(self.ref_audio_path),
            normalize_text=True,
            num_step=16,
            speed=1.0
        )
        audio_np = audio_tensor.squeeze().cpu().numpy()
        self._stream_and_play_audio(audio_np, sample_rate=24000)

    async def _speak_edge_tts(self, text: str) -> None:
        communicate = edge_tts.Communicate(text, self.voice_name)
        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if self._stop_requested:
                break
            if chunk["type"] == "audio":
                mp3_buffer.write(chunk["data"])

        if self._stop_requested:
            return

        mp3_buffer.seek(0)
        try:
            audio_data, sample_rate = sf.read(mp3_buffer)
            self._stream_and_play_audio(audio_data, sample_rate)
        except Exception as e:
            logger.error(f"[EdgeTTS] Playback error: {e}")

    def _stream_and_play_audio(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """Plays audio in blocks while calculating RMS amplitude throttled to 25 Hz for smooth UI rendering."""
        # Convert stereo to mono for amplitude calculation
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            mono_data = np.mean(audio_data, axis=1)
        else:
            mono_data = audio_data

        # Normalize audio array
        mono_data = mono_data.astype(np.float32)
        # Throttled chunk size to ~25 Hz (within the required 20-30 Hz range)
        chunk_size = int(sample_rate / 25)

        # Start non-blocking playback stream
        try:
            stream = sd.OutputStream(samplerate=sample_rate, channels=len(audio_data.shape) if len(audio_data.shape) > 1 else 1)
            stream.start()

            for i in range(0, len(mono_data), chunk_size):
                if self._stop_requested:
                    break

                chunk = mono_data[i : i + chunk_size]
                # Calculate RMS amplitude
                rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                # Scale between 0.0 and 1.0 with smoothing
                scaled_amp = min(1.0, max(0.0, rms * 3.5))
                self._emit_state(scaled_amp, "SPEAKING")

                # Write chunk to audio output
                if len(audio_data.shape) > 1:
                    raw_chunk = audio_data[i : i + chunk_size]
                else:
                    raw_chunk = chunk
                stream.write(raw_chunk)

            stream.stop()
            stream.close()

        except Exception as e:
            logger.debug(f"[AudioOutput] Output stream error: {e}")

    def stop(self) -> None:
        """Instantly halts any speech playback (Barge-In)."""
        self._stop_requested = True
        self.is_speaking = False
        try:
            sd.stop()
        except Exception:
            pass
        self._emit_state(0.0, "IDLE")

omnivoice_tts = OmniVoiceTTS()
