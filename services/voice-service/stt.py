"""
Speech-to-Text (STT) Module for J.A.R.V.I.S using faster-whisper.
"""
import io
import logging
import os
import wave
from pathlib import Path
from typing import BinaryIO, Optional
import numpy as np

logger = logging.getLogger("jarvis.voice.stt")


class SpeechToText:
    """
    High-performance transcription engine using CTranslate2/faster-whisper.
    """

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load_model(self) -> bool:
        if self.model is not None:
            return True
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading WhisperModel ({self.model_size}) on {self.device} ({self.compute_type})...")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info(f"WhisperModel ({self.model_size}) loaded successfully.")
            return True
        except Exception as e:
            logger.warning(f"Could not load faster-whisper model: {e}")
            return False

    def transcribe(
        self,
        audio_source: str | Path | bytes | io.BytesIO,
        language: str = "en",
        beam_size: int = 5,
        vad_filter: bool = True
    ) -> str:
        """
        Transcribes audio from a file path, BytesIO stream, or raw WAV bytes.
        """
        if not self.model:
            if not self.load_model():
                logger.error("STT engine unavailable: WhisperModel failed to load.")
                return ""

        try:
            # If raw bytes provided, wrap into BytesIO
            if isinstance(audio_source, bytes):
                audio_source = io.BytesIO(audio_source)

            segments, info = self.model.transcribe(
                audio_source,
                beam_size=beam_size,
                language=language,
                vad_filter=vad_filter
            )

            text_segments = [segment.text for segment in segments]
            full_text = " ".join(text_segments).strip()
            logger.debug(f"Transcribed audio ({info.duration:.2f}s): {full_text}")
            return full_text
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return ""

    def transcribe_pcm(
        self,
        pcm_data: bytes,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> str:
        """
        Helper to transcribe raw PCM 16-bit byte buffer by wrapping in WAV header.
        """
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        wav_buf.seek(0)
        return self.transcribe(wav_buf)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python stt.py <audio_file_path>", file=sys.stderr)
        sys.exit(1)
    audio_path = sys.argv[1]
    engine = SpeechToText()
    transcription = engine.transcribe(audio_path)
    print(transcription)

