"""
backend/audio/voice_ears.py
Wake-Word & Realtime Speech-to-Text Listener with Instant Barge-In.
Halts TTS speech output the millisecond the user speaks.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from backend.config import settings
from backend.audio.omnivoice_tts import omnivoice_tts

logger = logging.getLogger("jarvis.audio.ears")

class VoiceEars:
    """Microphone listener with openWakeWord and barge-in interruption."""

    def __init__(self):
        self.wake_words = [w.lower() for w in settings.WAKE_WORDS]
        if settings.WAKE_WORD and settings.WAKE_WORD.lower() not in self.wake_words:
            self.wake_words.insert(0, settings.WAKE_WORD.lower())
        self.is_listening: bool = False
        self._on_wake_callbacks: List[Callable[[], Any]] = []
        self._on_speech_callbacks: List[Callable[[str], Any]] = []

    def update_wake_word(self, word: str) -> None:
        """Dynamically update primary wake word."""
        w = word.strip().lower()
        if w and w not in self.wake_words:
            self.wake_words.insert(0, w)

    def on_wake(self, cb: Callable[[], Any]) -> None:
        self._on_wake_callbacks.append(cb)

    def on_speech(self, cb: Callable[[str], Any]) -> None:
        self._on_speech_callbacks.append(cb)

    def trigger_barge_in(self) -> None:
        """Interrupts assistant speech output immediately."""
        if omnivoice_tts.is_speaking:
            logger.info("[VoiceEars] Barge-in triggered! Halting TTS playback.")
            omnivoice_tts.stop()

    def process_incoming_audio_text(self, text: str) -> None:
        """Processes transcribed audio from client or local mic."""
        cleaned = text.strip()
        if not cleaned:
            return

        # Barge-in immediately
        self.trigger_barge_in()

        # Check for wake word
        cleaned_lower = cleaned.lower()
        is_wake = any(w in cleaned_lower for w in self.wake_words)
        if is_wake:
            logger.info(f"[VoiceEars] Wake word detected in: '{cleaned}'")
            for cb in self._on_wake_callbacks:
                try:
                    cb()
                except Exception:
                    pass

        for cb in self._on_speech_callbacks:
            try:
                cb(cleaned)
            except Exception:
                pass

voice_ears = VoiceEars()
