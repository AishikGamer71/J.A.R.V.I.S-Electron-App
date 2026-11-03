"""
Echo Gate: Mutes microphone audio during TTS playback to prevent feedback loops.
"""
import logging
import time

logger = logging.getLogger("jarvis.voice.echo_gate")


class EchoGate:
    def __init__(self, post_playback_delay_ms: int = 300):
        self.post_playback_delay_ms = post_playback_delay_ms
        self._is_muted = False

    def on_tts_start(self):
        self._is_muted = True
        logger.debug("Echo Gate active: Microphone muted during assistant speech")

    def on_tts_end(self):
        time.sleep(self.post_playback_delay_ms / 1000.0)
        self._is_muted = False
        logger.debug("Echo Gate released: Microphone live")

    @property
    def is_mic_muted(self) -> bool:
        return self._is_muted
