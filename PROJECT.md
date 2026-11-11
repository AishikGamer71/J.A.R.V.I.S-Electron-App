# Project: Unified J.A.R.V.I.S. Desktop System

## Architecture
- **Frontend**: Untouched React 19 / TypeScript / Electron UI with 9 navigation tabs (`DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`). Central holographic neural sphere tuned with `JARVIS_LIGHTING_CONFIG` in `src/components/widgets/arc-reactor.tsx`.
- **Backend Core**: Python FastAPI gateway on `127.0.0.1:8765` providing full REST endpoints and dual full-duplex WebSockets (`/ws` and `/ws/jarvis`).
- **Autonomous Brain**: Interruptible conversation loop, context compression, dynamic prompt building, parallel tool dispatch with loop guards, and 60s cron scheduler.
- **Memory & State Store**: SQLite WAL schema version 12 (`~/.jarvis/state.db`) with FTS5, Hybrid RAG (Reciprocal Rank Fusion $k=60$ combining FTS5 + FAISS), and Instinct continuous learning engine.
- **Security & ECC**: `AgentShield` with 14 regex patterns, destructive command blocking, config guard, and ECC pre/post tool hooks logging to `~/.jarvis/homunculus/observations.jsonl`.
- **Voice Pipeline**: Sub-32ms barge-in full-duplex audio pipeline, offline openWakeWord (`hey_jarvis_v0.1.onnx`), streaming RealtimeSTT (`faster-whisper`), and OmniVoice 24kHz voice cloning TTS microservice on port 8001.
- **Automation & Grounding**: Native COM UIAutomation bridge (`windows_mcp_bridge.py` excluding Electron HWND), OmniParser V2 icon detection & captioning microservice on port 8002, Agent-S3 runner with emergency abort hotkey, headless CDP browser-use, and MarkItDown document conversion.
- **Vision Senses & Mobile**: SPMC OpenCV webcam hub, MediaPipe air gestures, DeepFace Facenet512 Face ID with FasNet anti-spoofing, Crawl4AI, GPT-Researcher, and MobileRun ADB control.
- **Hardware Profiling & Power**: Dynamic CPU/RAM/VRAM hardware detector, telemetry store, and Win32 power guardian.
- **Multi-Environment**: Isolated `uv` environments (`.venv` for core, `.venv-omnivoice` for TTS, `.venv-omniparser` for UI parser) reconciled via `scripts/setup-environments.ps1`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Reference Audio Backup & Restore | Back up `backend/audio/assets/jarvis_ref.wav` to `_safe_assets/`, wipe legacy files, restore to `backend/voice/assets/jarvis_ref.wav` | M1 | R2.1, Phase 1.1 |
| 2 | Legacy Backend & Doc Clean Wipe | Clean wipe of all 24 legacy backend files, stubs, and 11 obsolete documentation `.md` files | M1 | R2.1, Phase 1.2-1.3 |
| 3 | Target Directory Structure | Create `backend/` directory tree (`agents/`, `memory/`, `skills/`, `core/`, `engine/`, `security/`, `voice/`, `automation/`, `senses/`, `hardware/`) | M1 | R2.2, Phase 2.1 |
| 4 | Workspace Governance Rules | Author `.antigravity/rules.md` and `.agent/rules/rules.md` (UI immutability, 3-tier routing, camera/mic ownership, ECC hooks) | M1 | R2.3, Phase 2.2 |
| 5 | Agent, Memory & Skill Profiles | Author profiles (`planner.md`, `architect.md`, `security_auditor.md`), memories (`SOUL.md`, `USER.md`, `MEMORY.md`), and skills | M1 | R2.4, Phase 2.3 |
| 6 | Arc Reactor & Sphere Tuning | Create `src/components/widgets/arc-reactor.tsx` with `JARVIS_LIGHTING_CONFIG` and delta-time animation loop; bridge with `sphere.tsx` | M1 | R1, Phase 6.6 |
| 7 | AgentShield 14 Secret Patterns | Implement regex scanning for 14 credential/secret types, destructive commands, config tampering, and prompt injection | M2 | R3.1, Phase 6.1 |
| 8 | ECCHookDispatcher & Homunculus Log | Implement pre/post tool hooks logging invocation metadata to `~/.jarvis/homunculus/observations.jsonl` | M2 | R3.1, Phase 6.1 |
| 9 | InstinctEngine & Dynamic Injection | Parse observations into behavioral instinct rules with confidence scoring and dynamic prompt injection | M2 | R3.1, Phase 6.1 |
| 10 | SessionDB SQLite WAL Schema 12 | Implement SQLite state database at `~/.jarvis/state.db` with schema version 12 and FTS5 search | M2 | R3.2, Phase 6.2 |
| 11 | ContextCompressor | Semantic summarization and pruning of message history exceeding token budgets | M2 | R3.2, Phase 3.2 |
| 12 | Dynamic PromptBuilder | Assembly of system instructions, SOUL/USER profiles, active instincts, tool definitions, and context into LLM prompt | M2 | R3.2, Phase 3.2 |
| 13 | ToolDispatcher & Parallel Workers | ThreadPool tool execution with 3-tier action validation, parallel dispatch, and loop guard | M2 | R3.2, Phase 6.2 |
| 14 | HermesBrain Conversation Loop | Asynchronous, interruptible conversation loop integrating context, model router, and tool dispatcher | M2 | R3.2, Phase 3.2 |
| 15 | CronScheduler | Background 60-second tick loop for periodic task execution and state maintenance | M2 | R3.2, Phase 3.2 |
| 16 | HardwareProfiler & TelemetryStore | System CPU/RAM/VRAM metric polling and dynamic capability detection | M3 | R3.3, Phase 6.3 |
| 17 | Multi-Engine ModelRouter | Heuristic and trace-driven routing across local Ollama, cloud providers, and fallback tiers | M3 | R3.3, Phase 6.3 |
| 18 | HybridMemory RRF k=60 | Hybrid RAG fusing SQLite FTS5 keyword search and FAISS vector embeddings via Reciprocal Rank Fusion | M3 | R3.3, Phase 6.3 |
| 19 | WakewordEngine | Offline wake-word detection using openWakeWord ONNX model (`hey_jarvis_v0.1.onnx`) | M3 | R3.4, Phase 3.4 |
| 20 | RealtimeSTT | Streaming speech-to-text using faster-whisper with automatic CPU fallback | M3 | R3.4, Phase 3.4 |
| 21 | OmniVoiceService Microservice | 24kHz zero-shot voice cloning TTS microservice listening on port 8001 | M3 | R3.4, Phase 3.4 |
| 22 | Full-Duplex AudioPipeline & Barge-In | Audio capture/playback pipeline with sub-32ms barge-in voice interruption | M3 | R3.4, Phase 6.4 |
| 23 | PowerGuardian | Win32 power and battery state monitoring for power-profile throttling | M3 | R3.4, Phase 3.4 |
| 24 | WindowsMCPBridge | Native COM UIAutomation bridge for Windows desktop accessibility excluding Electron HWND | M4 | R3.5, Phase 3.5 |
| 25 | OmniParserService Microservice | YOLOv9-E icon detection + Florence-2 captioning microservice listening on port 8002 | M4 | R3.5, Phase 3.5 |
| 26 | AgentS3Runner | OSWorldACI desktop runner with exact termination check and `Ctrl+Alt+Backspace` emergency abort | M4 | R3.5, Phase 3.5 |
| 27 | BrowserUseRunner | Headless background Chrome DevTools Protocol automation runner | M4 | R3.6, Phase 3.6 |
| 28 | MarkItDownService | Document conversion (PDF, DOCX, XLSX) to clean Markdown with OCR and table repair | M4 | R3.6, Phase 3.6 |
| 29 | CameraHub | SPMC OpenCV webcam frame broadcaster with simulated/mock fallback | M5 | R3.7, Phase 6.5 |
| 30 | MediaPipeGestures | Real-time air gesture recognition pipeline from 60 FPS camera frames | M5 | R3.7, Phase 3.7 |
| 31 | DeepFaceSentry | Facenet512 biometric authentication with FasNet anti-spoofing at 2 Hz | M5 | R3.7, Phase 3.7 |
| 32 | Crawl4AIService | Noise-free web scraping and Markdown extraction service | M5 | R3.6, Phase 3.6 |
| 33 | GPTResearcherService | Multi-source academic and web research synthesis engine | M5 | R3.6, Phase 3.6 |
| 34 | MobileRunService | Wireless Android ADB bridge and Portal WebSocket control | M5 | R3.7, Phase 3.7 |
| 35 | Unified REST API Gateway | FastAPI application on `127.0.0.1:8765` with health checks, system stats, sessions, history, tools, and memory APIs | M5 | R4.1, Phase 4 |
| 36 | Full-Duplex WebSocket Gateway | Dual `/ws` and `/ws/jarvis` WebSocket routes supporting `WebSocketEnvelope` and legacy telemetry events | M5 | R4.2, Phase 4 |
| 37 | Multi-Environment Bootstrap Script | PowerShell setup script `scripts/setup-environments.ps1` for `.venv`, `.venv-omnivoice`, `.venv-omniparser` | M5 | R5.1, Phase 5.1 |
| 38 | System Architecture Documentation | Comprehensive `README.md` and `docs/UNIFIED_ARCHITECTURE.md` documentation | M5 | R5.2, Phase 5.2 |
| 39 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test suite covering feature, boundary, cross-feature, and real-world scenarios | M6 | Acceptance Criteria |
| 40 | Adversarial Coverage Hardening (Tier 5) | White-box stress testing and gap mitigation driven by Challenger agents | M6 | Final Milestone Phase 2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Workspace Governance, Rules & UI Visualizer Tuning | Asset backup, legacy wipe, directory tree, governance rules, agent/skill profiles, `arc-reactor.tsx` lighting tuning | none | DONE |
| M2 | Security, Continuous Learning, Brain & State Store | AgentShield (14 patterns), ECCHookDispatcher, InstinctEngine, SessionDB schema 12, HermesBrain, ToolDispatcher, PromptBuilder, ContextCompressor, CronScheduler | M1 | DONE |
| M3 | Hardware Profiling, Routing, Hybrid RAG & Voice Pipeline | HardwareProfiler, TelemetryStore, ModelRouter, HybridMemory (RRF k=60), WakewordEngine, RealtimeSTT, OmniVoiceService (port 8001), AudioPipeline (barge-in), PowerGuardian | M2 | DONE |
| M4 | Desktop, Web & Document Automation | WindowsMCPBridge, OmniParserService (port 8002), AgentS3Runner, BrowserUseRunner, MarkItDownService | M2 | DONE |
| M5 | Vision Senses, Mobile, Unified Gateway & Multi-Env | CameraHub, MediaPipeGestures, DeepFaceSentry, Crawl4AI, GPTResearcher, MobileRun, Unified Gateway (`backend/main.py`), `setup-environments.ps1`, Architecture Docs | M3, M4 | DONE |
| M6 | Final Milestone: 100% E2E Test Suite & Adversarial Hardening | Tier 1-4 E2E Test Suite verification + Tier 5 Adversarial Coverage Hardening | M5, E2E Testing Track | DONE |

## Interface Contracts
### `backend/security/agent_shield.py`
- `AgentShield.scan_input(text: str) -> SecurityScanResult`
- `AgentShield.validate_command(cmd: str) -> bool`
- `AgentShield.sanitize_output(text: str) -> str`
- Returns dataclass `SecurityScanResult(passed: bool, violation_type: Optional[str], details: str)`

### `backend/memory/state_db.py`
- `SessionDB(db_path: Path = Path("~/.jarvis/state.db"))`
- `SessionDB.create_session(title: str) -> str`
- `SessionDB.add_message(session_id: str, role: str, content: str, tokens: int = 0) -> str`
- `SessionDB.get_messages(session_id: str, limit: int = 50) -> List[Dict]`
- `SessionDB.search_fts(query: str, limit: int = 20) -> List[Dict]`

### `backend/core/hermes_brain.py` ↔ `backend/main.py`
- `HermesBrain.run_turn(session_id: str, user_input: str, on_token: Callable[[str], None]) -> AsyncIterator[BrainEvent]`
- `HermesBrain.interrupt()` -> halts current LLM or tool execution immediately

### `backend/main.py` (FastAPI Gateway)
- `GET /health` -> `{"status": "healthy", "service": "jarvis-core-service", "version": "2.0.0"}`
- `GET /api/system/stats` -> `{"cpu_pct": float, "ram_used_mb": float, "ram_total_mb": float, "gpu_pct": float, "power": Dict}`
- `GET /v1/tools` -> `{"tools": List[ToolSchema]}`
- `POST /v1/tools/invoke` -> `{"tool": str, "args": dict}` -> `{"result": Any, "status": str}`
- `WebSocket /ws` & `/ws/jarvis` -> bidirectional JSON envelopes `{"type": str, "payload": Any, "timestamp": str}`

## Code Layout
- `backend/`
  - `agents/`: Agent role profiles (`planner.md`, `architect.md`, `security_auditor.md`)
  - `memory/`: Memory profiles (`SOUL.md`, `USER.md`, `MEMORY.md`), `state_db.py`, `hybrid_rag.py`, `instinct_engine.py`
  - `skills/`: Runtime skill definition markdowns
  - `core/`: `hermes_brain.py`, `prompt_builder.py`, `context_compressor.py`, `tool_dispatcher.py`, `cron_scheduler.py`
  - `engine/`: `hardware_profiler.py`, `model_router.py`, `telemetry_store.py`
  - `security/`: `agent_shield.py`, `ecc_hooks.py`
  - `voice/`: `wakeword_engine.py`, `realtime_stt.py`, `omnivoice_service.py`, `audio_pipeline.py`, `assets/jarvis_ref.wav`
  - `automation/`: `windows_mcp_bridge.py`, `omniparser_service.py`, `agent_s3_runner.py`, `browser_use_runner.py`, `markitdown_service.py`
  - `senses/`: `camera_hub.py`, `deepface_sentry.py`, `mediapipe_gestures.py`, `crawl4ai_service.py`, `gpt_researcher_service.py`, `mobilerun_service.py`
  - `hardware/`: `power_guardian.py`
  - `main.py`: Unified FastAPI REST & WebSocket entry point
- `src/components/widgets/arc-reactor.tsx`: Holographic neural visualizer with `JARVIS_LIGHTING_CONFIG` and delta-time animation
- `scripts/setup-environments.ps1`: Multi-environment isolated setup script
- `docs/UNIFIED_ARCHITECTURE.md`: Complete architecture specification
