# BRIEFING — 2026-11-10T11:55:00Z

## Mission
Investigate and design complete implementation blueprints for the 4 Milestone M3 backend modules: wakeword_engine, realtime_stt, omnivoice_service, and audio_pipeline.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, technical architect
- Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_3\
- Original parent: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
- Milestone: M3 (Voice Pipeline & Audio Services)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify project source files
- Fallback design: automatic fallback to simulated streams, mock modes, and CPU fallbacks when audio hardware / heavy neural libraries are absent
- Produce handoff.md with complete blueprints, data classes, schemas, state machine, and interface contracts

## Current Parent
- Conversation ID: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4
- Updated: 2026-11-10T11:47:30Z

## Investigation State
- **Explored paths**:
  - `backend/voice/assets/jarvis_ref.wav` (inspected: 24000 Hz, 1 channel, 176832 frames, 7.368s, 353708 bytes)
  - `tests/e2e/test_tier1_features.py` (lines 610-719: verified exact tests for Features 19, 20, 21, 22)
  - `tests/e2e/test_tier2_boundaries.py` (lines 160-190: verified sub-32ms boundaries & PCM zero/max/min edge cases)
  - `tests/e2e/test_tier3_combinations.py` (lines 84-95: conversational barge-in combo test)
  - `tests/e2e/test_tier4_scenarios.py` (lines 58-76: barge-in real-world scenario)
  - `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` (lines 284-300, 540-614: detailed specs for voice pipeline)
  - `.venv` environment packages (verified: `sounddevice` 0.5.6, `soundfile` 0.14.0, `edge-tts` 7.3.1 present; `openwakeword`, `faster_whisper`, `torch` absent in primary `.venv`)
  - `src/services/jarvisBridge.ts` & `src/lib/gateway-client.ts` (WebSocket events: `jarvis-voice-state`, `agent.state`, `agent.complete`)
- **Key findings**:
  - Primary `.venv` contains `sounddevice`, `soundfile`, `edge-tts`, and `numpy`, but lacks heavy ML packages (`torch`, `onnxruntime`, `openwakeword`, `faster-whisper`).
  - Strict fallback architecture is essential: all 4 modules must initialize cleanly in `.venv` without missing-module errors.
  - Sound device acquisition must be wrapped in `try/except` for `sd.PortAudioError` with automatic fallback to simulated audio frame generation and programmatic trigger.
  - Sub-32ms barge-in latency bound is achievable via immediate `threading.Event.set()` and non-blocking `sd.stop()`.
  - OmniVoice 24kHz service can leverage `edge-tts` + 24kHz resampling or synthetic RIFF WAV generator when isolated `.venv-omnivoice` is not yet running.
- **Unexplored areas**: None for M3 voice pipeline scope.

## Key Decisions Made
- Architecture blueprint specifies dual-mode operation for all 4 modules: Full Neural Pipeline (when GPU/weights available) and High-Fidelity Local Fallback (CPU/edge-tts/synthetic/mock) with 100% identical interfaces and schemas.
- Designed comprehensive data classes and state machine with states: `IDLE`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`.

## Artifact Index
- DISPATCH.md — record of initial dispatch message
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — complete M3 voice pipeline architectural blueprint and implementation specification
