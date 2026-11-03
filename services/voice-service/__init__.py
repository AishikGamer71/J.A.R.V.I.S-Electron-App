"""
J.A.R.V.I.S Voice Service Package
"""
try:
    from .stt import SpeechToText
    from .tts import TextToSpeech
    from .wake_word import WakeWordDetector
    from .echo_gate import EchoGate
except (ImportError, ValueError):
    from stt import SpeechToText
    from tts import TextToSpeech
    from wake_word import WakeWordDetector
    from echo_gate import EchoGate

__all__ = ["SpeechToText", "TextToSpeech", "WakeWordDetector", "EchoGate"]
