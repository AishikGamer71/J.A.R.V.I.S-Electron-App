"""
Text-to-Speech (TTS) Module for J.A.R.V.I.S using Piper neural voices and native fallbacks.
"""
import io
import logging
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.voice.tts")


class TextToSpeech:
    """
    Neural Text-to-Speech engine supporting Piper CLI, ONNX models, and platform fallback.
    """

    def __init__(
        self,
        voice_model: str = "en_US-ryan-high",
        model_path: Optional[str] = None,
        piper_bin: Optional[str] = None
    ):
        self.voice_model = voice_model
        self.model_path = model_path
        self.piper_bin = piper_bin or shutil.which("piper")
        self._fallback_engine = None

    def synthesize(self, text: str, output_wav_path: str | Path) -> bool:
        """
        Synthesize text directly to a target .wav file.
        """
        output_path = Path(output_wav_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Try Piper if binary exists
        if self.piper_bin and os.path.exists(self.piper_bin):
            try:
                cmd = [self.piper_bin, "--model", self.model_path or self.voice_model, "--output_file", str(output_path)]
                res = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=15)
                if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"Synthesized speech via Piper ({output_path.stat().st_size} bytes)")
                    return True
                logger.warning(f"Piper execution failed ({res.stderr.decode('utf-8', errors='ignore')}), using fallback.")
            except Exception as e:
                logger.warning(f"Piper TTS error: {e}, falling back to native TTS engine.")

        # 2. Native Engine Fallback (pyttsx3 / Windows SAPI5)
        return self._synthesize_native_fallback(text, output_path)

    def synthesize_bytes(self, text: str) -> bytes:
        """
        Synthesize text and return the generated WAV audio as bytes.
        """
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            success = self.synthesize(text, tmp_path)
            if success and tmp_path.exists():
                return tmp_path.read_bytes()
            return b""
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _synthesize_native_fallback(self, text: str, output_path: Path) -> bool:
        """
        Cross-platform fallback synthesizer using pyttsx3.
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Synthesized fallback speech via pyttsx3 ({output_path.stat().st_size} bytes)")
                return True
        except Exception as e:
            logger.error(f"pyttsx3 fallback failed: {e}")

        # Synthetic beep/silence WAV generator to prevent crash if all sound drivers fail
        return self._generate_synthetic_wav(output_path)

    def _generate_synthetic_wav(self, output_path: Path, duration_sec: float = 0.5) -> bool:
        try:
            import numpy as np
            sample_rate = 16000
            t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
            audio = (0.1 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())
            return True
        except Exception as e:
            logger.error(f"Synthetic WAV generation failed: {e}")
            return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        if len(sys.argv) == 2:
            out_file = sys.argv[1]
            text = sys.stdin.read().strip()
        else:
            print("Usage: python tts.py <text_or_file> <output_wav_path>", file=sys.stderr)
            sys.exit(1)
    else:
        text_arg = sys.argv[1]
        out_file = sys.argv[2]
        if os.path.exists(text_arg) and os.path.isfile(text_arg):
            text = Path(text_arg).read_text(encoding="utf-8").strip()
        else:
            text = text_arg

    tts = TextToSpeech()
    success = tts.synthesize(text, out_file)
    sys.exit(0 if success else 1)

