# DISPATCH LOG

## 2026-11-10T08:00:13Z
From: 0bb27719-4d7f-42ba-b6e4-6ef8044600dc (parent)
Execute a complete, production-ready backend replacement and 17-repository assimilation across all 6 phases for the unified J.A.R.V.I.S. Desktop Application while preserving the existing React/TypeScript/Electron UI.

Working directory: e:\Projects\J.A.R.V.I.S Electron App
Integrity mode: development

Reference material: c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md

## Requirements

### R1. UI Preservation and Holographic Sphere Tuning
Keep the existing React/TypeScript/Electron UI 100% visually untouched across all 9 navigation tabs (`DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`) and system control bar buttons, with only the following specified modifications:
1. Strip all upper buttons, top toolbar controls, and Ultron theme/mode/persona controls from `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts`.
2. Tune the central holographic sphere in `src/components/widgets/arc-reactor.tsx` using `JARVIS_LIGHTING_CONFIG` (balanced golden-amber palette, dark bronze outer containment ring, warm silver-gold inner core) and frame-rate-independent delta-time animation physics with exponential damping.
All remaining UI structure, styling, and widget components must remain visually intact.

### R2. Workspace Governance, Rules & Agent/Skill Profiles
1. Back up `backend/audio/assets/jarvis_ref.wav` to a temporary safe location, cleanly wipe all legacy backend Python files, stubs, and obsolete documentation Markdown files, then restore the reference voice prompt to `backend/voice/assets/jarvis_ref.wav`.
2. Establish the target `backend/` directory structure (`agents/`, `memory/`, `skills/`, `core/`, `engine/`, `security/`, `voice/`, `automation/`, `senses/`, `hardware/`).
3. Author workspace governance rules in `.antigravity/rules.md` and `.agent/rules/rules.md` establishing UI immutability, 3-tier action routing, single camera/mic ownership, and ECC hook enforcement.
4. Author agent profiles (`planner.md`, `architect.md`, `security_auditor.md`), memory profiles (`SOUL.md`, `USER.md`, `MEMORY.md`), and runtime skill definitions (`desktop_control.md`, `browser_background.md`, `deep_research.md`, `document_reader.md`, `vision_biometrics_gestures.md`, `mobile_adb_control.md`).

### R3. 17-Repository Code Assimilation
Execute repository-by-repository assimilation into `backend/` using temporary `_donor_staging/`, cleanly deleting staging folders upon assimilation:
1. **Security & Continuous Learning (ECC)**: Implement `AgentShield` in `backend/security/agent_shield.py` with 14 secret patterns, destructive command blocking, config-protection, and prompt injection scanning. Implement `ECCHookDispatcher` in `backend/security/ecc_hooks.py` with pre/post tool hooks logging to `~/.jarvis/homunculus/observations.jsonl`. Implement `InstinctEngine` in `backend/memory/instinct_engine.py` with confidence scoring and dynamic prompt injection.
2. **Autonomous Brain & State Store (Hermes Agent)**: Implement `SessionDB` in `backend/memory/state_db.py` (SQLite WAL schema version 12 at `~/.jarvis/state.db` with FTS5 search). Implement `ContextCompressor` in `backend/core/context_compressor.py`, dynamic prompt builder in `backend/core/prompt_builder.py`, `tool_dispatcher.py` with parallel workers and loop guards, `hermes_brain.py` with interruptible conversation loop, and `cron_scheduler.py` (60s tick loop).
3. **Hardware Profiling, Model Routing & Hybrid RAG (OpenJarvis)**: Implement `detect_hardware()` and real-time metric polling in `backend/engine/hardware_profiler.py` and `telemetry_store.py`. Implement multi-engine routing with trace-driven/heuristic policy in `backend/engine/model_router.py`. Implement `HybridMemory` in `backend/memory/hybrid_rag.py` using Reciprocal Rank Fusion (RRF k=60) combining SQLite FTS5 and FAISS embeddings.
4. **Voice Pipeline & Battery Guardian (OmniVoice, openWakeWord, RealtimeSTT)**: Implement offline wake-word detection in `backend/voice/wakeword_engine.py` (`hey_jarvis_v0.1.onnx`), streaming STT in `backend/voice/realtime_stt.py` (`faster-whisper-large-v3-turbo-ct2`), and 24kHz voice cloning TTS microservice on port 8001 (`backend/voice/omnivoice_service.py`). Implement full-duplex audio pipeline with sub-32ms barge-in and state broadcasting in `backend/voice/audio_pipeline.py`. Implement AC power and battery monitoring in `backend/hardware/power_guardian.py`.
5. **Desktop Automation & Grounding (Windows-MCP, OmniParser V2, Agent-S3)**: Implement native COM UIAutomation bridge in `backend/automation/windows_mcp_bridge.py` (excluding the J.A.R.V.I.S. Electron HWND to prevent UI deadlocks). Implement OmniParser V2 icon detection and captioning microservice on port 8002 (`backend/automation/omniparser_service.py`). Implement `AgentS3` runner with exact termination check and global emergency abort hotkey in `backend/automation/agent_s3_runner.py`.
6. **Web & Document Automation (Browser-Use, MarkItDown, Crawl4AI, GPT-Researcher)**: Implement headless background CDP browsing in `backend/automation/browser_use_runner.py`. Implement document conversion with OCR in `backend/automation/markitdown_service.py`. Implement fast noise-free Markdown extraction in `backend/senses/crawl4ai_service.py` and multi-source research reporting in `backend/senses/gpt_researcher_service.py`.
7. **Vision Senses & Mobile Control (DeepFace, MediaPipe, MobileRun)**: Implement SPMC OpenCV webcam hub in `backend/senses/camera_hub.py` feeding 60 FPS frames to `backend/senses/mediapipe_gestures.py` (air-gesture control) and 2 Hz frames to `backend/senses/deepface_sentry.py` (Facenet512 Face ID with FasNet anti-spoofing). Implement wireless Android ADB and Portal WebSocket control in `backend/senses/mobilerun_service.py`.

### R4. Unified REST & WebSocket Gateway
Implement `backend/main.py` listening on `127.0.0.1:8765`:
1. REST endpoints: `GET /health`, `GET /api/health`, `GET /api/env`, `POST /api/env`, `GET /api/system/stats`, `GET /api/history`, `POST /api/history/clear`, `GET /sessions`, `GET /api/sessions`, `GET /sessions/{session_id}/messages`, `DELETE /sessions/{session_id}`, `GET /search`, `GET /v1/tools`, `POST /v1/tools/invoke`, `GET /v1/core-memory`, `POST /v1/core-memory`, `GET /v1/audit`, `GET /v1/permissions`, `GET /v1/agents`, and `GET /v1/inbox`.
2. Full-duplex WebSocket endpoints (`/ws` and `/ws/jarvis`) handling all client commands (`system.toggle`, `vision.mode`, `audio.control`, `reset_abort`, `user.message`) and broadcasting `WebSocketEnvelope` / legacy bridge events (`agent.state`, `agent.token`, `agent.complete`, `tool.start`, `tool.result`, `system.metrics`, `jarvis-telemetry`, `jarvis-voice-state`, `jarvis-terminal-log`).

### R5. Multi-Environment Reconciliation & Documentation
1. Set up isolated Python environments using `uv` to avoid dependency conflicts: primary `.venv` (core services), `.venv-omnivoice` (`transformers>=5.3.0`, `torch>=2.4`), and `.venv-omniparser` (`transformers==4.40.0`, `numpy==1.26.4`), with a unified bootstrap script `scripts/setup-environments.ps1`.
2. Provide complete documentation in `README.md` and `docs/UNIFIED_ARCHITECTURE.md`.

## 2026-11-10T14:27:16Z
From: 0bb27719-4d7f-42ba-b6e4-6ef8044600dc (parent)
Status check

## 2026-11-10T14:28:55Z
From: 0bb27719-4d7f-42ba-b6e4-6ef8044600dc (parent)
Confirmed: Proceed with Option A. Re-dispatch the Milestone M4 verification subagents (reviewers, challengers, auditor) using Model="flash" so that the M4 gate evaluation completes without idling for primary model quota reset, and continue towards Milestone M5 upon certification.
