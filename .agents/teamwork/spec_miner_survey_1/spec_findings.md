# Comprehensive Specification Findings: Unified J.A.R.V.I.S. Desktop System

**Authoritative Sources**:
1. `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` (Master Execution Prompt for Antigravity)
2. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md` (Original User Request)
3. Existing Workspace Files (`src/shared/protocol.ts`, `src/services/jarvisBridge.ts`, `src/lib/gateway-client.ts`, `src/layouts/jarvis-layout.tsx`, `src/components/dashboard/sphere.tsx`, `package.json`, `scripts/run-jarvis-service.mjs`, `backend/`, `native_core/`)

---

## 1. Executive Summary & Architecture Overview

The J.A.R.V.I.S. desktop application is undergoing a complete, production-grade backend replacement and assimilation of 17 open-source repositories into a unified, modular Python backend listening on `http://127.0.0.1:8765` and `ws://127.0.0.1:8765/ws` (with legacy compatibility for `ws://127.0.0.1:8765/ws/jarvis`), while keeping the existing React/TypeScript/Electron UI 100% visually untouched across all 9 navigation tabs (`DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`).

The project enforces **strict workspace governance**:
- **Ironclad UI Immutability**: No visual UI modifications outside `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts`.
- **Pure J.A.R.V.I.S. Persona**: Removal of all Ultron controls, themes, and upper button clutter.
- **Calibrated Golden-Amber Holographic Visualizer**: Central neural sphere tuned via `JARVIS_LIGHTING_CONFIG` and frame-rate-independent delta-time animation physics with exponential damping.
- **3-Tier Action Routing**:
  1. Headless CDP web automation (`browser_use_runner.py`) & Markdown research (`crawl4ai_service.py`, `gpt_researcher_service.py`).
  2. Local document conversion (`markitdown_service.py`).
  3. Native Windows desktop automation (`windows_mcp_bridge.py` COM UIA `<10ms` -> `omniparser_service.py` YOLOv9-E/Florence-2 -> `agent_s3_runner.py`).
  4. Android mobile control (`mobilerun_service.py` wireless ADB `:5555` + Portal `:8080` / `:8081`).
- **Single Hardware Resource Ownership**: Single camera owner (`camera_hub.py` SPMC OpenCV hub feeding 60 FPS gestures to MediaPipe and 2 Hz BGR frames to DeepFace) and single microphone owner (`realtime_stt.py` feeding STT with sub-32ms barge-in).
- **ECC Security & Instincts**: Every tool execution passes through `agent_shield.py` (pre-validation) and `ecc_hooks.py` (post-logging to `observations.jsonl` for `instinct_engine.py`).

---

## 2. All 6 Phases of Backend Replacement

### Phase 0: Ironclad Workspace Laws
1. **Law 1 — Pure J.A.R.V.I.S. Holographic Sphere UI**:
   - Strip all upper buttons, top toolbar controls, and Ultron theme/mode/persona controls from `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts`.
   - Maintain pure black (`#000000`) background and golden-amber holographic sphere.
   - Calibrate lighting constants (`JARVIS_LIGHTING_CONFIG`) to prevent over-exposed white clipping or dim muddy visuals.
   - Implement frame-rate-independent 60–120 FPS animation physics using delta time (`dt = Math.min((now - lastTime) / 1000, 0.05)`) and exponential smoothing (`1 - Math.exp(-10 * dt)`).
   - Lock all 23 other core UI structure, styling, layout, and hook files.
2. **Law 2 — Allowed Bridge & Sidecar Wiring Files Only**:
   - Only data-binding logic in `src/shared/protocol.ts`, `src/services/jarvisBridge.ts`, `src/lib/gateway-client.ts`, `src/services/jarvis-ai-brain.ts`, `src/services/jarvis-voice-ai.ts`, `src/services/system-info.ts`, `src/services/hermes-adapter.ts`, `electron/*`, `scripts/run-jarvis-service.mjs`, and `package.json` may be inspected or wired.
3. **Law 3 — Clean Wipe of All Legacy Backend & Markdown Files Before Assimilation**:
   - Preserve `backend/audio/assets/jarvis_ref.wav` safely.
   - Delete all old backend Python files, legacy stubs, and old `.md` documentation files before authoring new governance and rules.
4. **Law 4 — Temporary Staging & Full Code Assimilation**:
   - Donor repositories (#2–#17) are shallow-cloned into temporary `_donor_staging/`, functional code is assimilated into `backend/`, and staging directories are cleanly deleted.

### Phase 1: Backup Voice Reference & Wipe Legacy Files
1. **1.1 Preserve Voice Reference**:
   - Copy `backend/audio/assets/jarvis_ref.wav` (353,708 bytes) to `_safe_assets/jarvis_ref.wav`.
2. **1.2 Delete 11 Existing `.md` Files**:
   - `README.md`
   - `.agent/rules/rules.md`
   - `.antigravity/rules.md`
   - `backend/skills/desktop_assistant.md`
   - `docs/ARC_REACTOR_VISUALIZER.md`
   - `docs/HERMES_MIGRATION.md`
   - `docs/JARVIS_SHOWCASE_SCRIPT.md`
   - `docs/PYTHON_BACKEND.md`
   - `docs/SWARM_ARCHITECTURE.md`
   - `docs/SYSTEM_DIAGNOSTIC.md`
   - `docs/SYSTEM_METRICS.md`
3. **1.3 Delete Existing `backend/` Logic & Legacy Stubs**:
   - Wipe `backend/__init__.py`, `config.py`, `main.py`, `requirements.txt`, `test_backend.py`, `test_e2e_ws.py`, `backend/audio/*`, `backend/automation/*`, `backend/core/*`, `backend/engine/*`, `backend/hardware/*`, `backend/memory/*`, `backend/security/*`.
   - Remove legacy directories: `apps/` (`apps/core-service`), `services/` (`services/voice-service`), `native_core/` (`native_core/__init__.py`), root `requirements.txt`, `test.cjs`, and `JARVIS_AI_Prototype_Showcase.pdf`.

### Phase 2: Create Workspace Rules, Agent Profiles & Skill Definitions
1. **2.1 Target Directory Tree**:
   ```
   backend/
   ├── __init__.py
   ├── config.py
   ├── main.py
   ├── agents/ (planner.md, architect.md, security_auditor.md)
   ├── memory/ (state_db.py, hybrid_rag.py, instinct_engine.py, MEMORY.md, USER.md, SOUL.md)
   ├── skills/ (desktop_control.md, browser_background.md, deep_research.md, document_reader.md, vision_biometrics_gestures.md, mobile_adb_control.md)
   ├── core/ (hermes_brain.py, prompt_builder.py, context_compressor.py, tool_dispatcher.py, cron_scheduler.py)
   ├── engine/ (hardware_profiler.py, model_router.py, telemetry_store.py)
   ├── security/ (ecc_hooks.py, agent_shield.py)
   ├── voice/ (wakeword_engine.py, realtime_stt.py, omnivoice_service.py, audio_pipeline.py, assets/jarvis_ref.wav)
   ├── automation/ (windows_mcp_bridge.py, omniparser_service.py, agent_s3_runner.py, browser_use_runner.py, markitdown_service.py)
   ├── senses/ (camera_hub.py, deepface_sentry.py, mediapipe_gestures.py, crawl4ai_service.py, gpt_researcher_service.py, mobilerun_service.py)
   └── hardware/ (power_guardian.py)
   ```
2. **2.2 Workspace Governance Rules**:
   - Create identical `.antigravity/rules.md` and `.agent/rules/rules.md` with:
     - Rule 1: UI Immutability (zero visual file edits, communicate via WS/REST).
     - Rule 2: 3-Tier Action Routing (CDP web -> MarkItDown -> Windows-MCP/OmniParser/Agent-S3 -> MobileRun).
     - Rule 3: Single Camera & Single Mic Ownership (SPMC Camera Hub, AudioToTextRecorder with barge-in).
     - Rule 4: ECC Security & Instincts (PreToolUse validation, PostToolUse logging to `~/.jarvis/homunculus/observations.jsonl`).
3. **2.3 Agent Profiles, Memory Profiles & Runtime Skills**:
   - `backend/agents/planner.md`: 4-stage implementation plan (Requirements -> Architecture Review -> Step Breakdown with Risk Levels -> Phased Order).
   - `backend/agents/architect.md`: ASCII data-flow diagrams, Trade-Off Analyses, ADR authoring.
   - `backend/agents/security_auditor.md`: Red-Team / Blue-Team / Auditor review against 102 rules.
   - `backend/memory/SOUL.md`: Canonical dry-witted, concise British AI persona with proactive hardware/security awareness.
   - `backend/memory/USER.md` & `MEMORY.md`: Persisted preferences, project contexts, learned facts.
   - 6 Skill definitions: `desktop_control.md`, `browser_background.md`, `deep_research.md`, `document_reader.md`, `vision_biometrics_gestures.md`, `mobile_adb_control.md`.

### Phase 3: Repository-By-Repository Code Assimilation
Assimilation of all 17 donor repositories (#2 through #17 into #1):
- **Repo #2 (ECC)**: `AgentShield` in `security/agent_shield.py`, `ECCHookDispatcher` in `security/ecc_hooks.py`, `InstinctEngine` in `memory/instinct_engine.py`.
- **Repo #3 (hermes-agent)**: `SessionDB` in `memory/state_db.py` (WAL schema 12), `ContextCompressor` in `core/context_compressor.py`, `prompt_builder.py`, `tool_dispatcher.py` (8 workers, loop guards), `hermes_brain.py` (interruptible conversation loop), `cron_scheduler.py` (60s tick).
- **Repo #4 (OpenJarvis)**: `detect_hardware()` in `engine/hardware_profiler.py`, `model_router.py` (multi-engine dispatcher, heuristic + trace-driven policy), `hybrid_rag.py` (RRF $k=60$ combining FTS5 and FAISS), `telemetry_store.py`.
- **Repo #5 (Agent-S) & Repo #11 (OmniParser)**: `omniparser_service.py` (YOLOv9-E + Florence-2 microservice on port 8002 in `.venv-omniparser`), `agent_s3_runner.py` (OSWorldACI, exact termination check fix Issue #235, `Ctrl+Alt+Backspace` emergency abort hotkey).
- **Repo #6 (OmniVoice), Repo #7 (openWakeWord), Repo #8 (RealtimeSTT)**: Restore `jarvis_ref.wav` to `voice/assets/`, `omnivoice_service.py` (24kHz voice cloning TTS microservice on port 8001 in `.venv-omnivoice`), `wakeword_engine.py` (`hey_jarvis_v0.1.onnx`), `realtime_stt.py` (`faster-whisper-large-v3-turbo-ct2`), `audio_pipeline.py` (sub-32ms barge-in), `power_guardian.py` (Win32 AC/battery polling every 50ms).
- **Repo #9 (browser-use), Repo #10 (Windows-MCP), Repo #12 (markitdown)**: `browser_use_runner.py` (headless background CDP), `windows_mcp_bridge.py` (COM UIA `<10ms`, excluding Electron HWND deadlock fix Issue #383), `markitdown_service.py` (in-memory Markdown conversion, OCR, `<sheetView showZeroes>` XML repair).
- **Repo #13 (deepface), Repo #14 (mediapipe), Repo #15 (crawl4ai), Repo #16 (gpt-researcher), Repo #17 (mobilerun)**: `camera_hub.py` (SPMC OpenCV webcam hub 60 FPS + 2 Hz), `mediapipe_gestures.py` (LIVE_STREAM, pinch click, swipe, scroll), `deepface_sentry.py` (Facenet512, YuNet, FasNet anti-spoofing, threshold 0.30), `crawl4ai_service.py` (PruningContentFilterLXML), `gpt_researcher_service.py` (BM25 lexical filter, multi-source research), `mobilerun_service.py` (wireless ADB `:5555`, Portal `:8080`, WebSocket `:8081` background listener).

### Phase 4: UI-To-Backend Linking Map
- Port `8765` FastAPI server in `backend/main.py`.
- REST endpoints and WebSocket protocols supporting both modern `/ws` and legacy `/ws/jarvis`.
- UI tab mapping across all 9 tabs (`DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`).

### Phase 5: Multi-Environment Reconciliation & Documentation
- Python environment isolation via `uv`:
  1. `.venv`: Python 3.12 primary environment for main server and general dependencies.
  2. `.venv-omnivoice`: Port 8001 microservice (`transformers>=5.3.0`, `torch>=2.4`).
  3. `.venv-omniparser`: Port 8002 microservice (`transformers==4.40.0`, `numpy==1.26.4`, `paddleocr<=2.8`, `ultralytics`).
- Unified bootstrap script: `scripts/setup-environments.ps1` and `scripts/setup-environments.sh`.
- Comprehensive documentation: `README.md` and `docs/UNIFIED_ARCHITECTURE.md`.
- Verification checklist: UI diff clean, backend/WS smoke test, 21-module clean import test.

### Phase 6: Code Blueprints & Schemas
- Detailed DDL for SQLite WAL schema version 12 (`~/.jarvis/state.db`).
- Model router heuristic reward function and Hybrid RAG RRF $k=60$ formulation.
- Full-duplex voice pipeline and barge-in event wiring.
- SPMC webcam hub implementation.
- 11 3-tier action tool schemas.
- Exact `JARVIS_LIGHTING_CONFIG` and physics constants for the holographic visualizer.

---

## 3. 17-Repository Assimilation Matrix

| # | Donor Repository | Source Template / Key Files | Assimilated Destination | Functional Core Assimilated |
|---|------------------|-----------------------------|-------------------------|-----------------------------|
| 1 | `AishikGamer71/J.A.R.V.I.S-Electron-App` | Workspace root, `src/`, `electron/` | Base App | Preserved React/TypeScript/Electron UI, window chrome, and audio-visualizer bindings. |
| 2 | `affaan-m/ECC` | `hooks/hooks.json`, `scripts/hooks/*`, `agents/planner.md`, `skills/security-scan/SKILL.md`, `skills/continuous-learning-v2/SKILL.md` | `backend/security/agent_shield.py`, `backend/security/ecc_hooks.py`, `backend/memory/instinct_engine.py`, `backend/agents/planner.md`, `backend/agents/architect.md`, `backend/agents/security_auditor.md` | 14 secret patterns, destructive command blocking, config-protection guard, pre/post tool hooks, confidence scoring (0.3–0.85), dynamic prompt injection. |
| 3 | `NousResearch/hermes-agent` | `run_agent.py`, `agent/conversation_loop.py`, `agent/prompt_builder.py`, `agent/context_compressor.py`, `agent/tool_executor.py`, `agent/tool_guardrails.py`, `model_tools.py`, `hermes_state.py`, `hermes_state_schema.py`, `cron/scheduler.py` | `backend/memory/state_db.py`, `backend/core/context_compressor.py`, `backend/core/prompt_builder.py`, `backend/core/tool_dispatcher.py`, `backend/core/hermes_brain.py`, `backend/core/cron_scheduler.py`, `backend/memory/SOUL.md`, `USER.md`, `MEMORY.md` | SQLite WAL Schema Version 12 (`~/.jarvis/state.db`), FTS5 multi-tokenizer search, 50% window context compressor, parallel tool executor (8 workers), loop guardrails, interruptible AIAgent, 60s cron scheduler. |
| 4 | `open-jarvis/OpenJarvis` | `src/openjarvis/core/config.py`, `src/openjarvis/engine/*`, `src/openjarvis/learning/*`, `src/openjarvis/tools/storage/*`, `src/openjarvis/telemetry/*` | `backend/engine/hardware_profiler.py`, `backend/engine/model_router.py`, `backend/memory/hybrid_rag.py`, `backend/engine/telemetry_store.py` | Hardware spec detection (CPU/RAM/GPU), multi-engine dispatcher (Ollama/Gemini/OpenAI/Anthropic), heuristic + trace-driven router ($R = 0.4S_{\text{lat}} + 0.3S_{\text{cost}} + 0.3S_{\text{tok}}$), Hybrid RAG RRF $k=60$ (`all-MiniLM-L6-v2` + SQLite FTS5). |
| 5 | `simular-ai/Agent-S` | `gui_agents/s3/agents/agent_s.py`, `worker.py`, `grounding.py`, `code_agent.py`, `common_utils.py`, `local_env.py` | `backend/automation/agent_s3_runner.py` | `AgentS3` multimodal desktop agent, `OSWorldACI` grounding, PyAutoGUI execution, exact termination check fix (`action[0].strip().upper() in ("DONE", "FAIL")`), `Ctrl+Alt+Backspace` emergency abort. |
| 6 | `k2-fsa/OmniVoice` | `omnivoice/cli/infer.py`, `omnivoice/models/omnivoice.py`, `omnivoice_flashinfer.py`, `audio.py` | `backend/voice/omnivoice_service.py` | 24kHz voice cloning TTS microservice on port 8001 (.venv-omnivoice), FlashInfer acceleration, pre-computed `jarvis_voice.pt` voice prompt caching. |
| 7 | `dscripka/openWakeWord` | `openwakeword/__init__.py`, `model.py`, `utils.py`, `vad.py` | `backend/voice/wakeword_engine.py` | 100% offline ONNX Runtime wake-word engine running `hey_jarvis_v0.1.onnx` on 16kHz mono audio. |
| 8 | `KoljaB/RealtimeSTT` | `RealtimeSTT/audio_recorder.py`, `audio_input.py`, `safepipe.py`, `core/` | `backend/voice/realtime_stt.py`, `backend/voice/audio_pipeline.py`, `backend/hardware/power_guardian.py` | Low-latency streaming STT (`faster-whisper-large-v3-turbo-ct2`), Silero + WebRTC dual VAD, sub-32ms barge-in, Win32 `GetSystemPowerStatus` polling (50ms). |
| 9 | `browser-use/browser-use` | `browser_use/agent/service.py`, `views.py`, `session.py`, `tools/service.py` | `backend/automation/browser_use_runner.py` | Headless Chrome/Edge background automation via CDP; executes web logins, forms, and extraction without cursor hijacking. |
| 10 | `CursorTouch/Windows-MCP` | `src/windows_mcp/` (`Desktop`, `TreeService`, `Snapshot`, `Click`, `Type`, `Drag`, `Shortcut`, `App`, `Clipboard`) | `backend/automation/windows_mcp_bridge.py` | Native COM UIAutomation bridge (<10ms interaction); explicit Electron HWND filtering to prevent UI deadlocks (Issue #383). |
| 11 | `microsoft/OmniParser` | `gradio_demo.py`, `util/utils.py`, `omnitool/omniparserserver/` | `backend/automation/omniparser_service.py` | Port 8002 microservice (.venv-omniparser) with YOLOv9-E icon detection + Florence-2 icon captioning; outputs Set-of-Mark labeled images and normalized coordinates. |
| 12 | `microsoft/markitdown` | `packages/markitdown/src/markitdown/_markitdown.py`, converters, `markitdown-ocr` | `backend/automation/markitdown_service.py` | Local document conversion (PDF, DOCX, XLSX, PPTX, YouTube, audio) with embedded image OCR and `<sheetView showZeroes>` XML repair. |
| 13 | `serengil/deepface` | `deepface/DeepFace.py`, `modeling.py`, `verification.py`, `FasNet.py` | `backend/senses/deepface_sentry.py` | Facenet512 Face ID with YuNet detector, FasNet anti-spoofing (MiniFASNetV2 + MiniFASNetV1SE), threshold 0.30 cosine distance, 2 Hz sentry check. |
| 14 | `google-ai-edge/mediapipe` | `mediapipe/tasks/python/vision/gesture_recognizer.py`, `hand_landmarker.py` | `backend/senses/mediapipe_gestures.py` | `LIVE_STREAM` 60 FPS gesture recognition (8 canned gestures), pinch ratio calculation ($\|L_4 - L_8\| / \|L_0 - L_9\|$), palm velocity swipe, two-finger vertical scroll. |
| 15 | `unclecode/crawl4ai` | `crawl4ai/async_webcrawler.py`, `async_configs.py`, `content_filter_strategy.py` | `backend/senses/crawl4ai_service.py` | High-speed headless web crawler returning noise-free `fit_markdown` via `PruningContentFilterLXML(threshold=0.48)` and BM25 filtering. |
| 16 | `assafelovic/gpt-researcher` | `gpt_researcher/agent.py`, `skills/researcher.py`, `skills/writer.py`, `context/lexical.py` | `backend/senses/gpt_researcher_service.py` | Multi-source research conductor with local BM25 context filtering, streaming progress to UI and generating cited Markdown reports. |
| 17 | `droidrun/mobilerun` | `mobilerun/agent/droid/droid_agent.py`, `manager_agent.py`, `executor_agent.py`, `tools/` | `backend/senses/mobilerun_service.py` | Wireless ADB (`:5555`) & Portal HTTP (`:8080`) / WebSocket (`:8081`) client; controls Android UI, reads notifications, SMS, battery alerts. |

---

## 4. Complete Specifications for All 21 Core Modules

### 1. `backend/core/hermes_brain.py`
- **Class**: `AIAgent`
- **Assimilated From**: `NousResearch/hermes-agent` (`run_agent.py`, `conversation_loop.py`)
- **Key Methods**:
  - `run_conversation(session_id: str, user_input: str, on_token: Callable, on_tool_start: Callable, on_tool_result: Callable) -> str`: Multi-turn conversational loop managing model dispatch, context compression, tool calling, and persistence.
  - `request_hard_interrupt()`: Immediately breaks active API streams and tool execution loops (wired to `reset_abort` and voice barge-in).
  - `delegate_task(subagent_name: str, task: str) -> str`: Spawns read-only subagents (`planner`, `architect`, `security_auditor`).
  - `_spawn_background_review()`: Background thread triggered after tool turns to update `MEMORY.md` and `USER.md`.
- **Dependencies**: `model_router`, `state_db`, `context_compressor`, `tool_dispatcher`, `prompt_builder`.

### 2. `backend/engine/model_router.py`
- **Class**: `ModelRouter`, `MultiEngineDispatcher`
- **Assimilated From**: `open-jarvis/OpenJarvis` (`learning/router.py`, `engine/*`)
- **Routing Context**:
  - `has_code`: checks for code blocks, `def `, `class `, `import `, `function `, `const `, `SELECT `, `=>`.
  - `has_math`: checks for `\frac`, `\int`, `\sum`, `\sqrt`, `solve`, `equation`, `matrix`, `eigenvalue`.
  - `urgency > 0.8` or `query_length < 50` -> Fast local Ollama (`http://127.0.0.1:11434`) or Google `gemini-2.5-flash`.
  - `has_code`, `has_math`, or `query_length > 500` -> Google `gemini-2.5-pro` or largest configured cloud model.
- **Trace-Driven Policy**:
  - Composite trace reward: $R = 0.4 \cdot S_{\text{latency}} + 0.3 \cdot S_{\text{cost}} + 0.3 \cdot S_{\text{tokens}}$ across 5 buckets (`code`, `math`, `short`, `long`, `general`) in `~/.jarvis/traces.db`.

### 3. `backend/memory/state_db.py`
- **Class**: `SessionDB`
- **Assimilated From**: `NousResearch/hermes-agent` (`hermes_state.py`, `hermes_state_schema.py`)
- **Database**: SQLite WAL mode at `~/.jarvis/state.db`.
- **Schema Version**: `SCHEMA_VERSION = 12`.
- **DDL Tables**: `schema_version`, `state_meta`, `system_prompts`, `sessions`, `messages`, `session_model_usage`, `messages_fts`, `messages_fts_trigram`, `messages_fts_cjk`.
- **Methods**: `create_session()`, `append_message()`, `get_messages()`, `list_sessions()`, `delete_session()`, `search_messages(query: str)`.

### 4. `backend/memory/hybrid_rag.py`
- **Class**: `HybridMemory`
- **Assimilated From**: `open-jarvis/OpenJarvis` (`tools/storage/hybrid.py`, `storage/sqlite.py`, `storage/faiss.py`)
- **Indexes**:
  - `SQLiteMemory`: FTS5 BM25 index on `~/.jarvis/memory.db`.
  - `FAISSMemory`: `sentence-transformers/all-MiniLM-L6-v2` 384-D cosine index (`faiss.IndexFlatIP`).
- **Reciprocal Rank Fusion**:
  $$\text{RRF}(d) = \sum_{i \in \{\text{fts}, \text{faiss}\}} \frac{w_i}{60 + \text{rank}_i(d)}$$
  Over-fetches $3 \times \text{top\_k}$ candidates per backend, returns top 5 chunks (`min_score=0.1`, `max_context_tokens=2048`).
- **Text Chunking**: `chunk_text(text, chunk_size=512, chunk_overlap=64)`.

### 5. `backend/memory/instinct_engine.py`
- **Class**: `InstinctEngine`
- **Assimilated From**: `affaan-m/ECC` (`skills/continuous-learning-v2/SKILL.md`, `instinct-cli.py`)
- **Data Path**: `~/.jarvis/homunculus/observations.jsonl` -> `~/.jarvis/homunculus/instincts/personal/`.
- **Confidence Scoring**:
  - 1–2 observations: `confidence = 0.3`
  - 3–5 observations: `confidence = 0.5`
  - 6–10 observations: `confidence = 0.7`
  - 11+ observations: `confidence = 0.85`
  - Confirm: `+0.05`, Contradict: `-0.10`, Decay: `-0.02 / week`.
- **Output**: Returns instincts with `confidence >= 0.7` for dynamic injection into system prompts via `prompt_builder.py`.

### 6. `backend/security/agent_shield.py`
- **Class**: `AgentShield`
- **Assimilated From**: `affaan-m/ECC` (`skills/security-scan/SKILL.md`) and native safety checks
- **Capabilities**:
  - 14 Secret detection patterns & high-entropy string scanner.
  - Destructive command blocker (`rm -rf`, `del /s /q`, `format`, `diskpart`, `mkfs`, `dd`, fork bombs, `shutdown`, registry deletion).
  - Config protection: blocks modifications to `.eslintrc*`, `tsconfig*.json`, `vite.config.ts`, `package.json`, `.env`, credentials, and locked `src/` files.
  - Prompt injection scanner (`scan_for_threats`) checking inputs and cron tasks.
  - Audit logging buffer exposed via `GET /v1/audit`.

### 7. `backend/voice/wakeword_engine.py`
- **Class**: `WakeWordEngine`
- **Assimilated From**: `dscripka/openWakeWord`
- **Model**: `hey_jarvis_v0.1.onnx` executed via ONNX Runtime CPU.
- **Audio Format**: 16kHz mono PCM, 80ms chunks (1280 samples `int16`).
- **Pipeline**: Audio chunk -> `melspectrogram.onnx` -> `embedding_model.onnx` -> `hey_jarvis_v0.1.onnx` classifier (`threshold=0.5`). 100% offline.

### 8. `backend/voice/realtime_stt.py`
- **Class**: `RealtimeSTTService`
- **Assimilated From**: `KoljaB/RealtimeSTT` (`AudioToTextRecorder`)
- **Models**:
  - Real-time stream: `tiny.en`
  - Final transcript: `deepdml/faster-whisper-large-v3-turbo-ct2`
- **VAD Parameters**: Silero VAD (`sensitivity=0.4`, deactivity detection), WebRTC VAD (`sensitivity=3`), post-speech silence `0.6s`, pre-recording buffer `1.0s`.

### 9. `backend/voice/omnivoice_service.py`
- **Microservice**: HTTP on `http://127.0.0.1:8001/tts` running in `.venv-omnivoice`.
- **Assimilated From**: `k2-fsa/OmniVoice`
- **Model**: `OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16, load_asr=False)`.
- **Optimizations**: `apply_flashinfer(model, enable_cuda_graph=True)`.
- **Voice Clone Caching**: On boot, creates `VoiceClonePrompt` from `backend/voice/assets/jarvis_ref.wav` and saves to `backend/voice/assets/jarvis_voice.pt`. Reuses cached prompt on every synthesis call with `num_step=16`, `guidance_scale=2.0`, `denoise=True`, `normalize_text=True`.
- **Output**: 24,000 Hz `float32` audio (~30x real-time), calls `torch.cuda.empty_cache()` post-synthesis.

### 10. `backend/automation/windows_mcp_bridge.py`
- **Class**: `WindowsMCPBridge`
- **Assimilated From**: `CursorTouch/Windows-MCP`
- **Tools Implemented**: `Snapshot`, `Click`, `Type`, `Drag`, `Shortcut`, `Wait`, `Scrape`, `Shell`, `App`, `Clipboard`.
- **Sub-10ms UIAutomation**: Native COM `comtypes`/`uiautomation`.
- **Critical Deadlock Fix (Issue #383)**: Explicitly filters out `HWND` belonging to `J.A.R.V.I.S-Electron-App` (`electron.exe` or window title matching `"JARVIS"`) from `other_windows_handles` in `TreeService.get_state()` so `Snapshot` never freezes the Electron UI thread.

### 11. `backend/automation/omniparser_service.py`
- **Microservice**: HTTP on `http://127.0.0.1:8002/parse` running in `.venv-omniparser` (`transformers==4.40.0`, `numpy==1.26.4`).
- **Assimilated From**: `microsoft/OmniParser`
- **Models**: YOLOv9-E (`weights/icon_detect_v3/model.pt`) and Florence-2 (`weights/icon_caption_florence`).
- **Parameters**: `BOX_TRESHOLD=0.05`, `iou_threshold=0.1`, `imgsz=640`, `output_coord_in_ratio=True`.
- **Output**: Set-of-Mark (`SoM`) labeled image with bounding boxes, parsed mark IDs, and Florence-2 semantic icon descriptions.

### 12. `backend/automation/agent_s3_runner.py`
- **Class**: `AgentS3Runner`
- **Assimilated From**: `simular-ai/Agent-S` (`AgentS3`, `Worker`, `OSWorldACI`, `CodeAgent`)
- **Grounding Integration**: Feeds screen capture to `omniparser_service.py` (`:8002/parse`), maps mark IDs to native screen coordinates, and executes PyAutoGUI actions.
- **Critical Fix (Issue #235)**: Exact termination check `if action[0].strip().upper() in ("DONE", "FAIL"):` before executing code.
- **Emergency Abort**: Global hotkey `Ctrl+Alt+Backspace` halts control in `<1ms`.

### 13. `backend/automation/browser_use_runner.py`
- **Class**: `BrowserUseRunner`
- **Assimilated From**: `browser-use/browser-use`
- **Execution**: Connects to background Chrome/Edge via Chrome DevTools Protocol (`CDP_URL` / headless `BrowserProfile`). Does not move or hijack the user's physical mouse cursor.
- **Model Integration**: Powered by `model_router.py` (Gemini or Ollama).

### 14. `backend/automation/markitdown_service.py`
- **Class**: `MarkItDownService`
- **Assimilated From**: `microsoft/markitdown` (`MarkItDown`, `markitdown-ocr`)
- **Formats Supported**: PDF, DOCX, XLSX, PPTX, YouTube URLs, audio, images, ZIP.
- **OCR Integration**: Embedded image OCR enabled (`priority = -1.0`).
- **XML Repair**: Automatic repair for corrupted `<sheetView showZeroes>` tags in `.xlsx` zip archives before parsing.

### 15. `backend/senses/camera_hub.py`
- **Class**: `JarvisCameraHub`
- **Architecture**: Single-Producer Multi-Consumer (SPMC) OpenCV webcam loop (`cv2.VideoCapture(0)`, `CAP_PROP_BUFFERSIZE=1`).
- **Distribution**:
  - MediaPipe: 60 FPS contiguous RGB frames directly to `mediapipe_gestures.py`.
  - DeepFace: Thread-safe `.copy()` BGR frame at 2 Hz (every 500ms) to `deepface_sentry.py`.
- **Lifecycle**: Activated on UI command `vision.mode: camera` or video toggle.

### 16. `backend/senses/deepface_sentry.py`
- **Class**: `DeepFaceSentry`
- **Assimilated From**: `serengil/deepface`
- **Configuration**: `model_name="Facenet512"`, `detector_backend="yunet"`, cosine distance threshold `0.30`.
- **Anti-Spoofing**: Dual-model FasNet (`MiniFASNetV2` 2.7x crop + `MiniFASNetV1SE` 4.0x crop).
- **Actions**:
  - Owner verified -> 24kHz OmniVoice greeting ("Welcome back, sir.").
  - Spoof or 3 consecutive unrecognized faces -> `STRANGER_SENTRY_ALERT`, snapshot saved to `~/.jarvis/sentry_logs/`, OmniVoice alert, locks destructive tools.

### 17. `backend/senses/mediapipe_gestures.py`
- **Class**: `MediaPipeGestures`
- **Assimilated From**: `google-ai-edge/mediapipe` (`GestureRecognizer`)
- **Mode**: `RunningMode.LIVE_STREAM` async callback.
- **Gestures Recognized**:
  - 8 Canned: `Closed_Fist`, `Open_Palm`, `Pointing_Up`, `Thumb_Down`, `Thumb_Up`, `Victory`, `ILoveYou`, `None`.
  - Pinch Click: $\text{PinchRatio} = \|L_4 - L_8\|_2 / \|L_0 - L_9\|_2$ (click when $< 0.28$, release when $> 0.38$).
  - Swipe: Palm velocity $v_x = \Delta x_9 / \Delta t$ for tab navigation (`SWIPE_LEFT`, `SWIPE_RIGHT`).
  - Scroll: Two-finger vertical delta $\Delta y = ((y_{8,t}+y_{12,t}) - (y_{8,t-1}+y_{12,t-1})) / 2$.

### 18. `backend/senses/crawl4ai_service.py`
- **Class**: `Crawl4AIService`
- **Assimilated From**: `unclecode/crawl4ai`
- **Crawler**: `AsyncWebCrawler(BrowserConfig(headless=True))`.
- **Configuration**: `CacheMode.BYPASS`, `remove_overlay_elements=True`, `remove_consent_popups=True`, `flatten_shadow_dom=True`.
- **Filter**: `DefaultMarkdownGenerator(content_filter=PruningContentFilterLXML(threshold=0.48, min_word_threshold=20))` + `BM25ContentFilter`. Returns high-speed `fit_markdown`.

### 19. `backend/senses/gpt_researcher_service.py`
- **Class**: `GPTResearcherService`
- **Assimilated From**: `assafelovic/gpt-researcher`
- **Configuration**: `SCRAPER="crawl4ai"`, `CONTEXT_FILTER="keyword"` (zero-cost local BM25 filter in `context/lexical.py`), LLM routed through `model_router.py`.
- **Output**: Real-time progress updates streamed via `tool.start` and `jarvis-terminal-log`, saves fully cited Markdown reports to `storage/reports/`.

### 20. `backend/senses/mobilerun_service.py`
- **Class**: `MobileRunService`
- **Assimilated From**: `droidrun/mobilerun`
- **Control Modes**: Wireless ADB (`:5555`) or Portal HTTP (`:8080`) Accessibility tree inspection.
- **Phone Actions**: Tap, swipe, Unicode typing via `MobilerunKeyboardIME`, launch apps, screenshot.
- **Background Portal Listener**: Persistent WebSocket connection to `ws://<PHONE_IP>:8081/?token=<TOKEN>` streaming `NOTIFICATION_POSTED`, `SMS_RECEIVED`, and `BATTERY_LOW` into J.A.R.V.I.S.'s inbox (`GET /v1/inbox`) and speech alerts.

### 21. `backend/hardware/power_guardian.py`
- **Class**: `PowerGuardian`
- **Assimilated From**: Windows Win32 API (`ctypes.windll.kernel32.GetSystemPowerStatus`) and `psutil`
- **Loop**: 50ms polling interval.
- **Events**:
  - AC unplugged (`ACLineStatus 1 -> 0`) or plugged (`0 -> 1`): Immediate 24kHz voice notification and `system.metrics` broadcast.
  - Critical battery thresholds (`20%`, `10%`): Emergency low-power alert and terminal log warning.

---

## 5. Supporting Modules & Architectural Infrastructure

### `backend/security/ecc_hooks.py`
- **Class**: `ECCHookDispatcher`
- **`pre_tool_use(tool_name: str, args: dict, session_id: str) -> bool`**: Validates command and path safety against `AgentShield`. Raises `PermissionError` if blocked.
- **`post_tool_use(tool_name: str, args: dict, result: any, duration_ms: float, session_id: str)`**: Appends a JSON line `{timestamp, session_id, tool_name, args, status, duration_ms}` to `~/.jarvis/homunculus/observations.jsonl`.

### `backend/core/context_compressor.py`
- **Class**: `ContextCompressor`
- **Compaction Rule**: When total message tokens exceed 50% of model context window, automatically summarizes intermediate conversation turns while preserving the head system prompt and recent tail turns. Sanitizes orphaned `tool_call` / `tool_result` pairs and marks compacted messages `active = 0` in SQLite.

### `backend/core/prompt_builder.py`
- **Methods**:
  - `load_soul_md()`: Loads `backend/memory/SOUL.md`.
  - `build_skills_system_prompt()`: Dynamically loads Markdown skill files from `backend/skills/*.md`.
  - `build_context_files_prompt()`: Injects `USER.md`, `MEMORY.md`, and instincts with `confidence >= 0.7` from `instinct_engine.py`.

### `backend/core/tool_dispatcher.py`
- **Class**: `ToolDispatcher`
- **Concurrency**: Parallel execution of read-only tools with `_MAX_TOOL_WORKERS = 8` and sequential barriers for mutating tools.
- **Loop Guardrails**: `identical_call_streak_halt` (halts identical repeated tool calls) and `identical_cycle_halt` (halts cyclic tool loops).
- **Security Hooks**: Wraps all invocations with `ecc_hooks.py`.

### `backend/core/cron_scheduler.py`
- **Class**: `CronScheduler`
- **Assimilated From**: `NousResearch/hermes-agent` (`cron/scheduler.py`)
- **Execution**: 60-second `tick()` loop protected by `.tick.lock`.
- **Security**: Runs `CronPromptInjectionBlocked` scan before executing any scheduled job prompt. Results pushed to `GET /v1/inbox`.

### `backend/voice/audio_pipeline.py`
- **Class**: `JarvisVoicePipeline`
- **Full-Duplex Barge-In**:
  - `_on_vad_start()` / `_on_recording_start()`: Immediately triggers `tts_stop_event.set()`, calls `sounddevice.stop()`, and broadcasts `{"type": "agent.state", "payload": {"state": "listening"}}`. Latency is `<32ms`.
  - `speak_24khz(text, session_id)`: Synthesizes audio via `omnivoice_service.py`, broadcasts `agent.complete` with base64 WAV audio for Arc Reactor Web Audio FFT, and plays via `sounddevice` at 24,000 Hz if not interrupted.

---

## 6. Complete REST & WebSocket API Specification

### Base Server URL
`http://127.0.0.1:8765`

### REST Endpoints
| HTTP Method | Route | Description | Request Body | Response Format |
|---|---|---|---|---|
| `GET` | `/health`, `/api/health` | System health check and module status | None | `{"status": "ok", "engine": str, "voice": str, "vision": str, "mobile": str}` |
| `GET` | `/api/env` | Read environment settings and config | None | `{"GOOGLE_API_KEY": "***", "OLLAMA_BASE_URL": str, ...}` |
| `POST` | `/api/env` | Update runtime environment settings | JSON dict of env vars | `{"status": "updated", "keys": list[str]}` |
| `GET` | `/api/system/stats` | Real-time hardware telemetry | None | `{hardware: SystemHardwareMetrics, network: SystemNetworkMetrics, uptime_seconds: float}` |
| `GET` | `/api/history` | Get chat history for default session | Query: `limit`, `session_id` | List of message objects |
| `POST` | `/api/history/clear` | Clear message history | Query or body: `session_id` | `{"status": "cleared", "session_id": str}` |
| `GET` | `/sessions`, `/api/sessions` | List all sessions from SessionDB | Query: `limit`, `offset` | List of session records from `sessions` table |
| `GET` | `/sessions/{session_id}/messages` | Get messages for specific session | None | List of message records from `messages` table |
| `DELETE` | `/sessions/{session_id}` | Delete a specific session | None | `{"status": "deleted", "session_id": str}` |
| `GET` | `/search` | Full-text search across messages | Query: `q` | List of matching message records via FTS5 |
| `GET` | `/v1/tools` | Enumerate all registered tool schemas | None | List of `ToolDefinition` objects |
| `POST` | `/v1/tools/invoke` | Direct tool execution from UI | `{"tool": str, "arguments": dict, "session_id": str}` | `ToolResultPayload` |
| `GET` | `/v1/core-memory` | Query hybrid RAG memory | Query: `q`, `top_k` | List of chunk objects with RRF scores |
| `POST` | `/v1/core-memory` | Ingest memory chunk into Hybrid RAG | `{"content": str, "metadata": dict}` | `{"status": "ingested", "id": str}` |
| `GET` | `/v1/audit` | Retrieve AgentShield audit logs | Query: `limit` | `{"grade": "A", "audit_logs": list[dict]}` |
| `GET` | `/v1/permissions` | Retrieve tool permissions & ECC hooks | None | `{"profile": "standard", "permissions": list[dict]}` |
| `GET` | `/v1/agents` | List subagent states & learned instincts | None | `{"agents": list[dict], "instincts": list[dict]}` |
| `GET` | `/v1/inbox` | Retrieve background notifications & alerts | None | List of notifications (cron, sentry, mobile, power) |

### WebSocket Endpoints
- `ws://127.0.0.1:8765/ws` (Modern endpoint used by `jarvisBridge.ts`)
- `ws://127.0.0.1:8765/ws/jarvis` (Legacy compatibility endpoint used by `gateway-client.ts`)

#### Client to Server Message Envelopes
1. **User Message**:
   ```json
   {
     "type": "user.message",
     "request_id": "uuid",
     "timestamp": "ISO-8601",
     "payload": {
       "content": "Hello Jarvis",
       "session_id": "default",
       "model": "optional-model-override"
     }
   }
   ```
2. **Audio Control**:
   ```json
   {
     "type": "audio.control",
     "payload": {
       "action": "start_listen | stop_listen | cancel_speech | synthesize",
       "text": "optional text to synthesize",
       "session_id": "default"
     }
   }
   ```
3. **Client Command**:
   ```json
   {
     "type": "client.command",
     "payload": {
       "command": "system.toggle | vision.mode | hud.minimize | hud.show | reset_abort",
       "payload": { "mode": "camera | screen" }
     }
   }
   ```
4. **Emergency Abort Reset**:
   ```json
   { "type": "reset_abort" }
   ```

#### Server to Client Broadcast Envelopes
1. **Agent State**:
   ```json
   {
     "type": "agent.state",
     "payload": {
       "state": "idle | listening | transcribing | thinking | executing_tool | speaking",
       "session_id": "default",
       "details": "string description"
     }
   }
   ```
2. **Agent Token (Streaming)**:
   ```json
   {
     "type": "agent.token",
     "payload": {
       "session_id": "default",
       "delta": "token string"
     }
   }
   ```
3. **Agent Complete**:
   ```json
   {
     "type": "agent.complete",
     "payload": {
       "session_id": "default",
       "content": "Full response text",
       "role": "assistant",
       "audio_base64": "base64-encoded WAV buffer",
       "mime_type": "audio/wav"
     }
   }
   ```
4. **Tool Start & Result**:
   ```json
   {
     "type": "tool.start",
     "payload": { "session_id": "default", "tool": "windows_mcp_click", "arguments": { "x": 100, "y": 200 } }
   }
   ```
   ```json
   {
     "type": "tool.result",
     "payload": { "session_id": "default", "tool": "windows_mcp_click", "result": true, "duration_ms": 8.4, "outcome": "SUCCESS" }
   }
   ```
5. **System Metrics & Legacy Envelopes**:
   - `system.metrics` / `jarvis-telemetry`: Broadcasts hardware and network metrics every 1.0s.
   - `jarvis-voice-state`: Real-time voice state and audio amplitude for 60 FPS Three.js rendering.
   - `jarvis-terminal-log`: Real-time logs from security checks, tool executions, and instincts.

---

## 7. SQLite WAL Schema Version 12 Specification (`~/.jarvis/state.db`)

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=30000;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS state_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_prompts (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'electron',
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    system_prompt_hash TEXT,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL DEFAULT 0.0,
    actual_cost_usd REAL DEFAULT 0.0,
    cost_status TEXT DEFAULT 'unknown',
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    cwd TEXT,
    profile_name TEXT,
    last_active_at REAL,
    active_pid INTEGER,
    active_updated_at REAL,
    resume_pending INTEGER DEFAULT 0,
    last_prompt_tokens INTEGER DEFAULT 0,
    hygiene_failure_streak INTEGER DEFAULT 0,
    hygiene_last_attempt_at REAL,
    hygiene_last_outcome TEXT,
    compression_failure_cooldown_until REAL DEFAULT 0,
    compression_failure_error TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_details TEXT,
    codex_reasoning_items TEXT,
    api_content TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    display_kind TEXT,
    message_uid TEXT,
    absorbed_message_uids TEXT,
    source_platform TEXT,
    source_user_id TEXT,
    source_user_name TEXT,
    source_chat_id TEXT,
    source_thread_id TEXT,
    source_message_id TEXT,
    turn_id TEXT,
    api_request_id TEXT
);

CREATE TABLE IF NOT EXISTS session_model_usage (
    session_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    base_url TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL,
    billing_mode TEXT NOT NULL DEFAULT 'standard',
    task TEXT NOT NULL DEFAULT 'conversation',
    api_calls INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    actual_cost_usd REAL DEFAULT 0.0,
    cost_status TEXT DEFAULT 'unknown',
    PRIMARY KEY (session_id, provider, base_url, model, billing_mode, task)
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
    content,
    content='messages',
    content_rowid='id',
    tokenize='trigram'
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_cjk USING fts5(
    content,
    content='messages',
    content_rowid='id'
);
```

---

## 8. Frontend Arc Reactor Visualizer & Holographic Sphere Specification

### Target File Rationale & Workspace Finding
- **Specification Source**: References `src/components/widgets/arc-reactor.tsx` for `JARVIS_LIGHTING_CONFIG` and physics constants.
- **Current Workspace Observation**: In the cloned repository, `src/components/widgets/arc-reactor.tsx` is currently absent; the visualizer is currently located in `src/components/dashboard/sphere.tsx` (imported by `src/pages/dashboard.tsx`).
- **Action for Implementation**: Create `src/components/widgets/arc-reactor.tsx` exporting `JARVIS_LIGHTING_CONFIG` and the calibrated Arc Reactor widget, ensuring seamless export/import compatibility with `src/components/dashboard/sphere.tsx` and `src/pages/dashboard.tsx`.

### Exact `JARVIS_LIGHTING_CONFIG` Constants
```typescript
export const JARVIS_LIGHTING_CONFIG = {
  background: '#000000',
  outerRingColor: 'rgba(78, 44, 15, 0.55)',              // Subtle dark bronze outer containment arc
  outerRingGapRadians: [Math.PI * 1.48, Math.PI * 1.66], // Top-right architectural gap
  circuitClusterColor: 'rgba(218, 160, 42, 0.76)',        // Mid-tone golden neural matrix (balanced, not dull)
  radialFilamentColor: 'rgba(242, 188, 62, 0.68)',        // Balanced golden radial spikes & rays
  innerCoreRingColor: 'rgba(225, 215, 190, 0.62)',        // Warm silver-gold inner core ring
  maxShadowBlur: 8,                                       // Capped glow preventing over-bright white clipping
  shadowColor: 'rgba(218, 160, 42, 0.32)',
  baseOpacity: 0.75,                                      // Prevents faded appearance during idle
  maxAudioBoostOpacity: 0.92,                             // Clamped peak brightness during speech
} as const;
```

### Delta-Time Animation Physics & Damping Parameters
```typescript
// Frame-rate-independent delta time (capped at 50ms to prevent jumps after background tab freeze)
const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05);
lastFrameTimeRef.current = timestamp;

// Exponential smoothing for audio reactivity and visual state transitions
const smoothing = 1 - Math.exp(-10 * dt);
smoothedAudioLevelRef.current += (rawAudioRms - smoothedAudioLevelRef.current) * smoothing;
smoothedGlowRef.current += (targetGlow - smoothedGlowRef.current) * (1 - Math.exp(-6 * dt));

// Multi-layer counter-rotation rates (radians per second)
outerArcAngleRef.current += 0.14 * dt;
midClusterAngleRef.current -= (0.22 + smoothedAudioLevelRef.current * 0.35) * dt;
innerCoreAngleRef.current += (0.38 + smoothedAudioLevelRef.current * 0.50) * dt;
```

---

## 9. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Security | Secret Redaction & Leak Blocking | Scans text and command arguments for 14 API key / token formats and high-entropy secrets | Plaintext command or output string | Redacted string or blocked command verdict | Raises `PermissionError` on leak attempt | Master Prompt §3.1 / ECC |
| 2 | Security | Destructive Command Blocking | Blocks dangerous OS-level commands (`rm -rf /`, `del /s /q`, `format`, `diskpart`, fork bombs) | Shell command string | Boolean safe flag + rejection reason | Returns `False` with security violation explanation | Master Prompt §3.1, §6.5 |
| 3 | Security | Config Protection Guard | Prevents tampering with project config files (`.eslintrc`, `tsconfig.json`, `vite.config.ts`, `package.json`, `.env`, `src/*`) | Target file path and write flag | Validation status | Blocks write/delete calls to protected paths | Master Prompt §3.1 |
| 4 | Security | Prompt Injection Scanner | Scans incoming user messages, tool results, and cron tasks for prompt override attacks | Text payload | Threat boolean + sanitized text | Blocks cron execution if threat detected | Master Prompt §3.1, §3.2 |
| 5 | Security | Pre & Post ECC Tool Hooks | Pre-validates tools with AgentShield; logs execution metrics to `observations.jsonl` | Tool name, arguments, execution duration, result | Observations log entry | Catches exceptions, logs `status: ERROR` | Master Prompt §3.1, §6.5 |
| 6 | Memory | Continuous Learning Instincts | Parses observations, maintains YAML instincts with confidence scoring (0.3–0.85) | Observation stream | Atomic instincts with `confidence >= 0.7` | Automatically decays inactive instincts (-0.02/wk) | Master Prompt §3.1 |
| 7 | Memory | SQLite WAL State Database | High-performance state and message persistence at `~/.jarvis/state.db` | SQL transactions, session and message payloads | Rows in SQLite WAL schema 12 | SQLite busy timeout 30,000ms with retry | Master Prompt §3.2, §6.1 |
| 8 | Memory | FTS5 Multi-Tokenizer Search | Tri-virtual-table full-text search (`messages_fts`, `trigram`, `cjk`) | Query string | Ranked message rows with match highlights | Returns empty list on malformed query | Master Prompt §3.2, §6.1 |
| 9 | Memory | Dynamic Context Compressor | Soft-compacts conversation history when tokens exceed 50% of model window | List of conversation messages | Compacted messages with preserved head/tail | Falls back to truncation if compaction fails | Master Prompt §3.2 |
| 10 | Memory | Hybrid RAG with RRF | Merges SQLite FTS5 BM25 and FAISS embeddings using Reciprocal Rank Fusion ($k=60$) | Query string, top_k | Top ranked text chunks with fused scores | Falls back to single index if one fails | Master Prompt §3.3, §6.2 |
| 11 | Engine | Hardware Profiler & Telemetry | Detects CPU, RAM, GPU, VRAM, battery, and powers `GET /api/system/stats` | System sensor polling | `SystemHardwareMetrics` structure | Fallback defaults if sensors unavailable | Master Prompt §3.3, §4.1 |
| 12 | Engine | Multi-Engine Model Router | Routes requests to Ollama, Gemini, OpenAI, or Anthropic via heuristics and trace rewards | User prompt, context metadata | Streamed or completed LLM response | Auto-fallbacks to local Ollama on cloud failure | Master Prompt §3.3, §6.2 |
| 13 | Voice | Offline Wake-Word Detection | Detects "Hey Jarvis" 100% offline via `hey_jarvis_v0.1.onnx` on CPU | 16kHz mono audio stream | Wake-word trigger event | Resets audio buffer on framing error | Master Prompt §3.5, §6.3 |
| 14 | Voice | Realtime Streaming STT | Continuous transcription using Faster-Whisper Large V3 Turbo with Silero/WebRTC VAD | Microphone PCM stream | Realtime partial and final transcripts | Recovers recorder pipe on silence timeout | Master Prompt §3.5, §6.3 |
| 15 | Voice | 24kHz Voice Cloning TTS | Generates cloned J.A.R.V.I.S. voice on port 8001 via OmniVoice and FlashInfer | Text string, voice clone prompt | 24kHz float32 audio waveform | Calls `torch.cuda.empty_cache()` post-synthesis | Master Prompt §3.5, §6.3 |
| 16 | Voice | Sub-32ms Full-Duplex Barge-In | Instantly halts TTS audio playback and resets state upon user speech detection | VAD speech start trigger | Audio stream halt + state switch to `listening` | Discards stale audio buffers immediately | Master Prompt §3.5, §6.3 |
| 17 | Automation | Windows-MCP Native UIA Bridge | Executes sub-10ms desktop UIAutomation clicks, typing, shortcuts, snapshots | Window coordinates, keystrokes, app names | UI state tree or action confirmation | Filters Electron HWND to prevent deadlocks | Master Prompt §3.6, §6.5 |
| 18 | Automation | OmniParser V2 Vision Grounding | Parses desktop screenshots into bounding boxes and icon captions on port 8002 | RGB screenshot image | Set-of-Mark image + normalized coordinates | Returns empty list if no elements detected | Master Prompt §3.4, §6.5 |
| 19 | Automation | Agent-S3 Multimodal Desktop Runner | Grounded desktop task automation using OmniParser V2 coordinates and PyAutoGUI | Natural language desktop task | Executed GUI actions | Halts on emergency abort hotkey (`Ctrl+Alt+Backspace`) | Master Prompt §3.4, §6.5 |
| 20 | Automation | Headless Background Browser-Use | Executes web navigation, logins, and form fills via Chrome/Edge CDP | High-level web instruction | Final web action result / extracted data | Recovers page session on tab crash | Master Prompt §3.6, §6.5 |
| 21 | Automation | In-Memory Document Converter | Converts PDF, DOCX, XLSX, PPTX, YouTube into Markdown with OCR | File path or YouTube URL | Clean Markdown text | Repairs corrupted XLSX zip XML tags | Master Prompt §3.6, §6.5 |
| 22 | Senses | SPMC OpenCV Webcam Hub | Grabs webcam frames once and distributes to 60 FPS MediaPipe and 2 Hz DeepFace | Webcam video stream | Frame buffer references | Silently yields if webcam unavailable | Master Prompt §3.7, §6.4 |
| 23 | Senses | MediaPipe Air-Gesture Recognizer | Detects canned gestures, pinch clicks, swipe navigation, two-finger scroll | 60 FPS RGB video frames | Gesture events broadcast over WebSocket | Ignores low-confidence hand landmark loss | Master Prompt §3.7, §6.4 |
| 24 | Senses | DeepFace Sentry & Face ID | Biometric owner verification and stranger sentry detection with FasNet anti-spoofing | 2 Hz BGR video frames | `OWNER_VERIFIED` or `STRANGER_SENTRY_ALERT` | Flags spoof attempt if liveness check fails | Master Prompt §3.7, §6.4 |
| 25 | Senses | Fast Web Extractor (Crawl4AI) | Rapid noise-free Markdown extraction using pruning content filters | Target URL, optional CSS/query | Clean `fit_markdown` | Returns empty content if page unreachable | Master Prompt §3.7, §6.5 |
| 26 | Senses | Deep Research Agent (GPT-Researcher) | Conducts multi-query research with local BM25 context filtering | Research query and report type | Comprehensive cited Markdown report | Falls back to search summary on timeout | Master Prompt §3.7, §6.5 |
| 27 | Senses | Android Mobile Control (MobileRun) | Controls Android smartphone via wireless ADB and Portal WebSocket listener | Mobile action goal or touch coordinate | Android UI execution or notification payload | Reconnects Portal WS on disconnection | Master Prompt §3.7, §6.5 |
| 28 | Hardware | Power & Battery Guardian | Win32 power status polling every 50ms with charger disconnect and low-battery alerts | Win32 system power status | Voice alert and UI telemetry updates | Fallback to `psutil.sensors_battery()` | Master Prompt §3.5, §6.3 |
| 29 | UI / Visual | Calibrated Holographic Arc Reactor | Golden-amber 3D neural sphere visualizer with delta-time physics and damping | Web Audio FFT stream, agent state | Rendered WebGL/Canvas frame | Clamps additive alpha to avoid white blowout | Master Prompt §0, §6.6 |

---

## 10. Edge Cases & Known Traps

| # | Feature | Input / Trigger | Observed Behavior & Authoritative Countermeasure |
|---|---------|-----------------|--------------------------------------------------|
| 1 | Agent-S3 Execution Check | Agent output containing "done" in arbitrary text (e.g., `is_done = False`) | **Trap**: `if "done" in code[0].lower()` triggers false task completion. **Fix**: Strictly check `if action[0].strip().upper() in ("DONE", "FAIL"):` before running `exec()`. |
| 2 | Windows-MCP UI Lockup | Snapshot or tree inspection while Electron app is active | **Trap**: Querying the Electron app's own HWND deadlocks the COM UIAutomation thread. **Fix**: Filter out any HWND whose process is `electron.exe` or title contains `"JARVIS"` from `other_windows_handles`. |
| 3 | OmniVoice Synthesis Latency | Synthesis call without pre-computed voice clone prompt | **Trap**: Generating the voice clone prompt from `jarvis_ref.wav` on every sentence adds ~1.5s overhead. **Fix**: Pre-compute `jarvis_voice.pt` once on boot and reuse it; call `torch.cuda.empty_cache()` post-synthesis. |
| 4 | RealtimeSTT Audio Stream Freeze | High-noise environments or rapid switching between speech and silence | **Trap**: RealtimeSTT buffer deadlock or VAD sensitivity drift. **Fix**: Dual VAD configuration (Silero VAD `0.4` + WebRTC VAD `3`), post-speech silence `0.6s`, pre-recording buffer `1.0s`. |
| 5 | OmniParser Dependency Conflict | Modern `transformers` versions (>4.40) or NumPy 2.x | **Trap**: Florence-2 / YOLOv9-E crash with attribute and tensor errors. **Fix**: Isolate OmniParser into `.venv-omniparser` with pinned `transformers==4.40.0` and `numpy==1.26.4`. |
| 6 | Camera Device Hardware Lock | MediaPipe and DeepFace attempting to open `cv2.VideoCapture(0)` concurrently | **Trap**: Windows MSMF/DirectShow device lock error (device already in use). **Fix**: Single-Producer Multi-Consumer (SPMC) hub in `camera_hub.py` opens camera once and distributes memory copies. |
| 7 | Full-Duplex Audio Echo / Barge-In | User speaks while TTS is playing through laptop speakers | **Trap**: STT transcribes J.A.R.V.I.S.'s own voice, creating a feedback loop. **Fix**: `on_vad_start` immediately sets `tts_stop_event.set()` and calls `sounddevice.stop()` in `<32ms`. |
| 8 | Grounding Out-of-Bounds Clicks | OmniParser returns normalized coordinates `[0.0, 1.0]` on multi-monitor setups | **Trap**: Clicks land on wrong monitor or offset coordinate. **Fix**: Map normalized coordinates to primary monitor bounding rect (`GetSystemMetrics(SM_CXSCREEN)` / `SM_CYSCREEN`). |
| 9 | Corrupted XLSX Spreadsheet Files | User uploads an Excel file with malformed XML tags | **Trap**: OpenPyXL / MarkItDown fails with XML parse exception. **Fix**: Pre-parse `.xlsx` zip archive and strip invalid `<sheetView showZeroes>` tags before invoking converter. |
| 10 | Background Tab Animation Freezing | User switches tabs, causing `requestAnimationFrame` to pause | **Trap**: Large delta time on tab resume causes particle explosion or physics warp. **Fix**: Clamp delta time strictly: `const dt = Math.min((timestamp - lastFrameTimeRef.current) / 1000, 0.05);`. |
| 11 | Desktop Emergency Stop | Autonomous agent starts erratic mouse or keyboard behavior | **Trap**: User loses mouse control and cannot click the stop button. **Fix**: Hardware interrupt hotkey `Ctrl+Alt+Backspace` detected via Win32 `GetAsyncKeyState` latches emergency abort in `<1ms`. |
| 12 | Visualizer Target File Discrepancy | Project expects `src/components/widgets/arc-reactor.tsx`, but workspace has `src/components/dashboard/sphere.tsx` | **Observation**: `arc-reactor.tsx` is referenced as the target for `JARVIS_LIGHTING_CONFIG`, while the existing codebase imports `sphere.tsx`. **Fix**: Implement `arc-reactor.tsx` with clean exports and calibrate `sphere.tsx` to align with the golden-amber lighting specification. |
