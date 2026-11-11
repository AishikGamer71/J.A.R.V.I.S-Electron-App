## 2026-11-10T11:47:07Z
You are explorer_m3_3, a technical exploration agent for Milestone M3 (Voice Pipeline & Audio Services).

Your parent orchestrator conversation ID is: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
Your working directory is: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_3\

MANDATORY FIRST STEP:
Read e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md and e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md before doing anything else.
Also inspect reference material: c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md (specifically Phase 3 & R3 sections for Voice Pipeline: OmniVoice, openWakeWord, RealtimeSTT).

MISSION:
Investigate and design complete implementation blueprints for the following 4 Milestone M3 backend modules:
1. `backend/voice/wakeword_engine.py`:
   - Offline wake-word detection using openWakeWord ONNX model (`hey_jarvis_v0.1.onnx`).
   - Handles audio stream chunking at 16kHz 16-bit mono PCM.
   - Fallback design: On hosts without a physical microphone (or when audio device cannot be opened), automatically falls back to a simulated audio stream or programmatic trigger mode (`simulate_wakeword()`, mock stream generator), never raising unhandled exceptions or crashing the service.
2. `backend/voice/realtime_stt.py`:
   - Streaming Speech-to-Text using RealtimeSTT / `faster-whisper-large-v3-turbo-ct2` (or CPU/mock fallback when offline).
   - Voice Activity Detection (VAD) integration (e.g. Silero VAD or energy-based VAD).
   - Emits partial transcripts and final finalized user transcripts.
3. `backend/voice/omnivoice_service.py`:
   - Standalone FastAPI/HTTP microservice running on port 8001.
   - 24kHz voice cloning TTS service utilizing reference audio prompt at `backend/voice/assets/jarvis_ref.wav` (which is already verified and backed up).
   - Endpoints: `GET /health`, `POST /synthesize` (accepts text, returns audio/wav or streaming audio chunks).
   - CPU-compatible and mock-synthesis fallback if heavy PyTorch/CUDA libraries are not present in `.venv`.
4. `backend/voice/audio_pipeline.py`:
   - Full-duplex conversational audio coordinator:
     - Coordinates Wakeword -> STT -> HermesBrain -> OmniVoice TTS -> Audio Playback.
     - Sub-32ms barge-in: when user starts speaking while TTS is playing, instantly signals `HermesBrain.interrupt()` and halts audio output.
     - Broadcasts audio state changes (`jarvis-voice-state`, `LISTENING`, `THINKING`, `SPEAKING`, `IDLE`) via WebSocket to React visualizer.

OUTPUT REQUIREMENTS:
Do NOT write or modify the implementation files yourself (read-only exploration).
Write your complete technical blueprint and recommendations to:
`e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_3\handoff.md`
Include:
- Exact data classes, schemas, and state machine transitions
- Method signatures and interface contracts
- Exact simulated stream and CPU fallback strategies for environments without mic/GPU
- Concrete code structure ready for Worker implementation

Send a message to your parent orchestrator (0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4) when done.
