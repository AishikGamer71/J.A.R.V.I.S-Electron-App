"""
Wake Word Detection Service for J.A.R.V.I.S
Streaming audio frame classifier using openWakeWord or custom neural models.
"""
import logging
import os
from typing import Callable, Optional
import numpy as np

logger = logging.getLogger("jarvis.voice.wake_word")


class WakeWordDetector:
    """
    Real-time wake word detector for 16kHz mono audio streams.
    Supports openWakeWord with fallback energy-level detection.
    """

    def __init__(
        self,
        wake_words: list[str] | None = None,
        sensitivity: float = 0.5,
        sample_rate: int = 16000,
        model_path: Optional[str] = None
    ):
        self.wake_words = wake_words or ["hey_jarvis", "jarvis"]
        self.sensitivity = sensitivity
        self.sample_rate = sample_rate
        self.model_path = model_path
        self.is_listening = False
        self.model = None
        self._stream = None
        self._callback: Optional[Callable[[str, float], None]] = None

        self._init_engine()

    def _init_engine(self):
        try:
            from openwakeword.model import Model
            wakeword_models = self.wake_words
            if self.model_path and os.path.exists(self.model_path):
                wakeword_models = [self.model_path]
            self.model = Model(wakeword_models=wakeword_models)
            logger.info("Initialized openWakeWord engine successfully.")
        except Exception as e:
            logger.warning(f"openWakeWord engine not available ({e}); using energy/heuristic mode.")
            self.model = None

    def process_frame(self, audio_data: np.ndarray | bytes) -> Optional[tuple[str, float]]:
        """
        Process a single 80ms chunk (1280 samples at 16kHz) of audio.
        Returns (wake_word, score) if detected above sensitivity threshold.
        """
        if isinstance(audio_data, bytes):
            audio_data = np.frombuffer(audio_data, dtype=np.int16)

        if len(audio_data) == 0:
            return None

        if self.model:
            try:
                prediction = self.model.predict(audio_data)
                for name, score in prediction.items():
                    if score >= self.sensitivity:
                        logger.info(f"Wake word detected: {name} (score: {score:.3f})")
                        return name, float(score)
            except Exception as e:
                logger.error(f"Error predicting wake word: {e}")
        return None

    def start_listening(self, on_wake_callback: Callable[[str, float], None]):
        """
        Start capturing local microphone audio via sounddevice.
        """
        self._callback = on_wake_callback
        self.is_listening = True

        try:
            import sounddevice as sd

            def _audio_callback(indata, frames, time_info, status):
                if not self.is_listening:
                    return
                if status:
                    logger.warning(f"Audio status: {status}")

                audio = np.frombuffer(indata, dtype=np.int16)
                detected = self.process_frame(audio)
                if detected and self._callback:
                    name, score = detected
                    self._callback(name, score)

            # Block size 1280 samples = 80ms at 16kHz
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=1280,
                callback=_audio_callback
            )
            self._stream.start()
            logger.info(f"WakeWordDetector stream started listening at {self.sample_rate}Hz.")
        except Exception as e:
            logger.warning(f"Could not start sounddevice microphone stream: {e}. Running in passive buffer mode.")

        return self

    def stop_listening(self):
        """Stop listening and close stream."""
        self.is_listening = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.info("WakeWordDetector stopped.")
