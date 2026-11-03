# J.A.R.V.I.S Voice Service

High-performance real-time speech subsystem for the J.A.R.V.I.S desktop platform.

## Architecture
- **STT**: `faster-whisper` (CTranslate2-accelerated Whisper models).
- **TTS**: `piper-tts` neural voice synthesis with native fallback.
- **Wake Word**: `openWakeWord` streaming neural activation detector.
- **Echo Gate**: Dynamic microphone suppression during synthesis playback.
- **AEC**: Chromium WebRTC Echo Cancellation in Electron renderer.
