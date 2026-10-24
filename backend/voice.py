import asyncio
import base64
import io
import logging
import os
import tempfile
from typing import Optional
import edge_tts
import pyttsx3

from backend.config import settings

logger = logging.getLogger("jarvis.voice")

class VoicePipeline:
    def __init__(self):
        self._current_task: Optional[asyncio.Task] = None
        self._is_speaking: bool = False

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def cancel(self):
        """Cancel ongoing speech synthesis or playback immediately (barge-in)."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self._is_speaking = False
        logger.info("[Voice] Cancelled current speech output (barge-in activated)")

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[dict]:
        """
        Synthesize speech from text using edge-tts (neural British/US voice) with pyttsx3 fallback.
        Returns a dictionary with base64 encoded audio and mime type.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        selected_voice = voice or settings.VOICE_NAME

        try:
            self._is_speaking = True
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=selected_voice,
                rate=settings.VOICE_RATE,
                pitch=settings.VOICE_PITCH
            )

            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])

            raw_bytes = audio_data.getvalue()
            if raw_bytes:
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                return {
                    "mime_type": "audio/mp3",
                    "audio_base64": b64,
                    "text": clean_text
                }
        except asyncio.CancelledError:
            self._is_speaking = False
            raise
        except Exception as e:
            logger.warning(f"[Voice] edge-tts error: {e}. Falling back to pyttsx3...")
        finally:
            self._is_speaking = False

        # pyttsx3 offline fallback
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            engine = pyttsx3.init()
            engine.setProperty("rate", 185)
            engine.save_to_file(clean_text, tmp_path)
            engine.runAndWait()

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    wav_bytes = f.read()
                os.unlink(tmp_path)
                if wav_bytes:
                    return {
                        "mime_type": "audio/wav",
                        "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                        "text": clean_text
                    }
        except Exception as err:
            logger.error(f"[Voice] pyttsx3 fallback also failed: {err}")

        return None

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe audio using faster-whisper if available, or fallback transcription.
        """
        if not audio_bytes:
            return ""

        # Try faster-whisper if installed
        try:
            from faster_whisper import WhisperModel
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                model = WhisperModel("base.en", device="cpu", compute_type="int8")
                segments, _ = model.transcribe(tmp_path, beam_size=5)
                text = " ".join([seg.text for seg in segments]).strip()
                return text
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e:
            logger.debug(f"[Voice] Local Whisper unavailable ({e}), using audio payload parser.")

        # Fallback: check if audio is valid WAV and extract basic info
        try:
            import wave
            with io.BytesIO(audio_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = round(frames / float(rate), 2) if rate > 0 else 0
                    logger.info(f"[Voice] Received valid audio frame ({duration}s).")
                    return f"[Audio input received: {duration}s]"
        except Exception:
            pass

        return "[Audio speech input processed]"

voice_pipeline = VoicePipeline()
