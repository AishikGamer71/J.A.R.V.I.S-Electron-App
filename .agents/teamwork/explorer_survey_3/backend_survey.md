# Backend & Environment Audit Report: J.A.R.V.I.S. Desktop System

**Auditor:** teamwork_explorer (`explorer_survey_3`)  
**Date:** 2026-11-10T08:18:00Z  
**Target:** Parent Orchestrator (`0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`)  
**Scope:** `backend/` directory, Python virtual environments, system hardware & runtimes (Python/uv/CUDA), voice reference asset, donor staging & repositories, and frontend-backend touchpoints.

---

## 1. Executive Summary

This survey provides a comprehensive, ground-truth audit of the existing backend, runtime dependencies, and system environment for the J.A.R.V.I.S. Electron App.

### Core Discoveries
1. **Voice Reference Audio Asset**: `backend/audio/assets/jarvis_ref.wav` is present and verified on disk (353,708 bytes, 24,000 Hz, 16-bit Mono PCM, 7.368s duration, SHA-256: `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`). It must be safeguarded to `_safe_assets/jarvis_ref.wav` prior to any deletion.
2. **Legacy Backend Footprint**: `backend/` currently contains 24 files across `audio/`, `automation/`, `core/`, `engine/`, `hardware/`, `memory/`, `security/`, and `skills/`. Every single Python file and stub corresponds precisely to the Phase 1.3 legacy wipe list.
3. **Environment & Hardware Profile**:
   - Host CPU: Intel(R) Core(TM) i3-10105 @ 3.70 GHz (4 cores / 8 logical processors), 16 GB visible RAM.
   - Host GPU: Integrated Intel(R) UHD Graphics 630. **No discrete NVIDIA GPU or CUDA runtime is present.**
   - Python: Python 3.11.9 is active in `.venv` and on the system PATH.
   - `uv`: High-speed Python package manager `uv 0.11.32` is fully installed and functional at `C:\Users\utpal\AppData\Local\hermes\bin\uv.exe`.
   - `uv python list` confirms local presence of CPython 3.11.9, CPython 3.12.12, and CPython 3.14.3.
4. **Donor Repositories & Staging**:
   - `_donor_staging/` does not exist currently.
   - TCP connectivity to `github.com:443` is verified (`TcpTestSucceeded: True`).
   - Donor Repo #3 (`NousResearch/hermes-agent`) is already physically cloned and present locally on this machine at `C:\Users\utpal\AppData\Local\hermes\hermes-agent` (contains `run_agent.py`, `hermes_state.py`, `model_tools.py`, `agent/`, `cron/`).
5. **Frontend-Backend Contract & Critical Health Check Gate**:
   - Electron sidecar runtime in `electron/jarvis-service-runtime.ts` line 143 explicitly checks `body?.status === 'healthy'`. `GET /health` must return `{"status": "healthy", ...}` to satisfy the startup gate.
   - The frontend uses two concurrent WebSocket entry points: `ws://127.0.0.1:8765/ws` (`jarvisBridge.ts`) and `ws://127.0.0.1:8765/ws/jarvis` (`gateway-client.ts`). `backend/main.py` must bind both routes.

---

## 2. Voice Reference Audio Verification

| Property | Value | Verification Method |
| :--- | :--- | :--- |
| **Current Location** | `E:\Projects\J.A.R.V.I.S Electron App\backend\audio\assets\jarvis_ref.wav` | Direct filesystem check |
| **Target Restored Location** | `backend/voice/assets/jarvis_ref.wav` | Specified in Phase 1.1 & Phase 2.1 |
| **Temporary Backup Location** | `_safe_assets/jarvis_ref.wav` | Specified in Phase 1.1 |
| **File Size** | `353,708` bytes (~345.4 KB) | `Get-Item` Length |
| **Audio Format** | Standard RIFF WAVE format | Python `wave` module |
| **Audio Channels** | `1` (Mono) | `wave.getnchannels()` |
| **Sample Width** | `2` bytes (16-bit PCM) | `wave.getsampwidth()` |
| **Sample Rate** | `24,000` Hz (24 kHz) | `wave.getframerate()` |
| **Frame Count** | `176,832` frames | `wave.getnframes()` |
| **Exact Audio Duration** | `7.368` seconds | `frames / framerate` |
| **SHA-256 Checksum** | `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73` | `Get-FileHash` SHA256 |

### Operational Guidance for Phase 1
- **Step 1**: Execute `New-Item -ItemType Directory -Path "_safe_assets" -Force`
- **Step 2**: Execute `Copy-Item "backend/audio/assets/jarvis_ref.wav" "_safe_assets/jarvis_ref.wav" -Force`
- **Step 3**: Re-verify checksum of `_safe_assets/jarvis_ref.wav` against the hash above before deleting `backend/`.

---

## 3. Existing `backend/` Inventory & Legacy Deletion Scope

### Current File Inventory (24 Files Total)

| File Path | Size (Bytes) | Lines | Purpose / Current State | Action in Phase 1.3 |
| :--- | :--- | :--- | :--- | :--- |
| `backend/__init__.py` | 89 | 4 | Package initializer | Delete |
| `backend/config.py` | 3,934 | 107 | Legacy Pydantic settings | Delete |
| `backend/main.py` | 20,209 | 592 | Legacy FastAPI + WebSocket gateway | Delete |
| `backend/requirements.txt` | 282 | 16 | Legacy backend dependencies | Delete |
| `backend/test_backend.py` | 7,437 | 175 | Legacy verification suite | Delete |
| `backend/test_e2e_ws.py` | 4,611 | 108 | Legacy WebSocket test script | Delete |
| `backend/audio/assets/jarvis_ref.wav` | 353,708 | 2,462 (raw) | **Core voice prompt asset** | **PRESERVE** |
| `backend/audio/omnivoice_tts.py` | 7,675 | 203 | Legacy TTS implementation | Delete |
| `backend/audio/voice_ears.py` | 2,386 | 70 | Legacy wake word listener | Delete |
| `backend/automation/desktop_controller.py`| 5,389 | 150 | Legacy pyautogui automation | Delete |
| `backend/automation/s3/agent_s3.py` | 2,606 | 69 | Legacy S3 runner stub | Delete |
| `backend/automation/s3/common_utils.py` | 1,483 | 47 | Legacy S3 utility functions | Delete |
| `backend/automation/s3/grounding.py` | 5,738 | 149 | Legacy bounding box grounding | Delete |
| `backend/core/agent_loop.py` | 12,999 | 327 | Legacy Gemini conversation loop | Delete |
| `backend/core/context_compressor.py` | 2,944 | 76 | Legacy middle-turn compressor | Delete |
| `backend/core/planner.py` | 3,873 | 102 | Legacy 4-stage planner stub | Delete |
| `backend/core/skill_and_cron.py` | 7,109 | 192 | Legacy cron tick loop | Delete |
| `backend/core/tool_registry.py` | 3,514 | 100 | Legacy in-memory tool catalog | Delete |
| `backend/engine/inference_router.py` | 14,948 | 348 | Legacy model routing logic | Delete |
| `backend/hardware/power_guardian.py` | 4,098 | 97 | Legacy Win32 power status poll | Delete |
| `backend/memory/instinct_learner.py` | 6,095 | 153 | Legacy instinct storage | Delete |
| `backend/memory/knowledge_rag.py` | 5,818 | 154 | Legacy TF-IDF RAG stub | Delete |
| `backend/memory/state_store.py` | 8,920 | 216 | Legacy session store | Delete |
| `backend/security/agent_shield.py` | 3,699 | 86 | Legacy regex safety validator | Delete |
| `backend/skills/desktop_assistant.md` | 344 | 10 | Legacy markdown skill definition | Delete |

### Auxiliary Legacy Directories & Files to Wipe
- `apps/core-service/` (contains old pytest stubs and unlinked venv)
- `services/voice-service/` (legacy decoupled service stub)
- `requirements.txt` (root level, 473 bytes)
- `test.cjs` (root level test script, 488 bytes)
- `JARVIS_AI_Prototype_Showcase.pdf` (19.8 MB legacy artifact)
- Note: `native_core/` should be cleanly restructured: keep `native_core/jarvis_native_fallback.py` ctypes bridge if Rust compilation is not active, but remove obsolete stub packages.

### Markdown Files Status
The master prompt lists 11 markdown files to wipe. Our inventory confirms:
- **Present and to be deleted in Phase 1.2**:
  - `README.md` (root)
  - `.agent/rules/rules.md`
  - `.antigravity/rules.md`
  - `backend/skills/desktop_assistant.md`
  - `docs/ARCHITECTURE_DECISION.md`
  - `docs/SECURITY_MODEL.md`
  - `docs/SKILL_AUTHORING.md`
- **Already absent**: `docs/ARC_REACTOR_VISUALIZER.md`, `docs/HERMES_MIGRATION.md`, `docs/JARVIS_SHOWCASE_SCRIPT.md`, `docs/PYTHON_BACKEND.md`, `docs/SWARM_ARCHITECTURE.md`, `docs/SYSTEM_DIAGNOSTIC.md`, `docs/SYSTEM_METRICS.md`.

---

## 4. Hardware, Python & Runtime Environment Audit

### System Specifications
- **Operating System**: Windows 10/11 x64 (NT kernel)
- **Processor**: Intel(R) Core(TM) i3-10105 CPU @ 3.70 GHz (4 physical cores, 8 logical processors)
- **RAM**: ~16 GB (~15.74 GB visible to OS)
- **Graphics Controller**: Intel(R) UHD Graphics 630 (Driver: 31.0.101.2140).
- **GPU Architecture**: **Integrated CPU graphics only.** No NVIDIA discrete GPU, no CUDA cores, and no `nvidia-smi` utility.

### Critical Architecture Implication: CPU-Only & Fallback Strategy
Because this workstation does not feature an NVIDIA GPU or CUDA:
1. `OmniVoice` (`backend/voice/omnivoice_service.py`): Cannot bind `device="cuda:0"` or use FlashInfer directly without failing. Must specify CPU device fallback or load simulated synthetic TTS / edge-tts audio when CUDA is unavailable.
2. `RealtimeSTT` (`backend/voice/realtime_stt.py`): Uses `faster-whisper-large-v3-turbo-ct2`. Must configure compute type `int8` or `float32` on `device="cpu"`.
3. `openWakeWord` (`backend/voice/wakeword_engine.py`): Operates cleanly on CPU via ONNX Runtime CPU execution provider.
4. `OmniParser V2` (`backend/automation/omniparser_service.py`): YOLOv9 and Florence-2 must load on `device="cpu"` (or provide mock box coordinates in offline smoke verification).
5. `DeepFace` & `MediaPipe`: Both run natively on CPU via OpenCV, YuNet, and MediaPipe CPU TFLite models.

### Python & UV Tooling Verification
- **Current Virtual Environment (`.venv`)**:
  - Python version: `Python 3.11.9`
  - Located at `e:\Projects\J.A.R.V.I.S Electron App\.venv`
  - Contains FastAPI 0.162.0, Uvicorn 0.54.0, WebSockets 17.4, Pydantic 2.14.2, Google GenAI 2.34.0, OpenAI 3.42.1, PyAutoGUI 0.9.54, SoundDevice 0.5.6.
- **`uv` Package Manager**:
  - Version: `uv 0.11.32 (3010295ae 2026-07-23 x86_64-pc-windows-msvc)`
  - Binary location: `C:\Users\utpal\AppData\Local\hermes\bin\uv.exe`
  - Confirmed Python runtimes available to `uv`:
    - CPython 3.14.3 (`C:\Users\utpal\AppData\Roaming\uv\python\cpython-3.14.3-windows-x86_64-none\python.exe`)
    - CPython 3.12.12 (`C:\Users\utpal\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe`)
    - CPython 3.11.9 (`E:\Computer Software\python\Py 3.11.9\python.exe`)

---

## 5. Donor Repositories & Local Staging Audit

### 17 Donor Repositories Mapping

| # | Donor Repository | Upstream URL | Target Backend Subsystem | Local Status |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `AishikGamer71/J.A.R.V.I.S-Electron-App` | Host Workspace | Electron UI, layout, React widgets | Cloned (host workspace) |
| **2** | `affaan-m/ECC` | `https://github.com/affaan-m/ECC.git` | `agent_shield.py`, `ecc_hooks.py`, `instinct_engine.py` | To clone into `_donor_staging/ECC` |
| **3** | `NousResearch/hermes-agent` | `https://github.com/NousResearch/hermes-agent.git` | `state_db.py`, `hermes_brain.py`, `prompt_builder.py`, `cron_scheduler.py` | **Locally Cached** at `C:\Users\utpal\AppData\Local\hermes\hermes-agent` |
| **4** | `open-jarvis/OpenJarvis` | `https://github.com/open-jarvis/OpenJarvis.git` | `hardware_profiler.py`, `model_router.py`, `hybrid_rag.py`, `telemetry_store.py` | To clone into `_donor_staging/OpenJarvis` |
| **5** | `simular-ai/Agent-S` | `https://github.com/simular-ai/Agent-S.git` | `agent_s3_runner.py` (OSWorldACI, fix Issue #235) | To clone into `_donor_staging/Agent-S` |
| **6** | `k2-fsa/OmniVoice` | `https://github.com/k2-fsa/OmniVoice.git` | `omnivoice_service.py` (24kHz cloning port 8001) | To clone into `_donor_staging/OmniVoice` |
| **7** | `dscripka/openWakeWord` | `https://github.com/dscripka/openWakeWord.git`| `wakeword_engine.py` (`hey_jarvis_v0.1.onnx`) | To clone into `_donor_staging/openWakeWord` |
| **8** | `KoljaB/RealtimeSTT` | `https://github.com/KoljaB/RealtimeSTT.git` | `realtime_stt.py`, `audio_pipeline.py`, `power_guardian.py` | To clone into `_donor_staging/RealtimeSTT` |
| **9** | `browser-use/browser-use` | `https://github.com/browser-use/browser-use.git`| `browser_use_runner.py` (CDP background browser) | To clone into `_donor_staging/browser-use` |
| **10** | `CursorTouch/Windows-MCP` | `https://github.com/cursortouch/windows-mcp.git`| `windows_mcp_bridge.py` (COM UIA, fix Issue #383) | To clone into `_donor_staging/windows-mcp` |
| **11** | `microsoft/OmniParser` | `https://github.com/microsoft/OmniParser.git` | `omniparser_service.py` (YOLOv9 + Florence-2 port 8002)| To clone into `_donor_staging/OmniParser` |
| **12** | `microsoft/markitdown` | `https://github.com/microsoft/markitdown.git` | `markitdown_service.py` (OCR + XLSX repairs) | To clone into `_donor_staging/markitdown` |
| **13** | `serengil/deepface` | `https://github.com/serengil/deepface.git` | `deepface_sentry.py` (Facenet512 + FasNet anti-spoof) | To clone into `_donor_staging/deepface` |
| **14** | `google-ai-edge/mediapipe` | `https://github.com/google-ai-edge/mediapipe.git`| `mediapipe_gestures.py` (60 FPS gestures), `camera_hub.py` | To clone into `_donor_staging/mediapipe` |
| **15** | `unclecode/crawl4ai` | `https://github.com/unclecode/crawl4ai.git` | `crawl4ai_service.py` (fast noise-free Markdown) | To clone into `_donor_staging/crawl4ai` |
| **16** | `assafelovic/gpt-researcher`| `https://github.com/assafelovic/gpt-researcher.git`| `gpt_researcher_service.py` (multi-source RAG reports) | To clone into `_donor_staging/gpt-researcher`|
| **17** | `droidrun/mobilerun` | `https://github.com/droidrun/mobilerun.git` | `mobilerun_service.py` (wireless ADB + Portal WS 8081)| To clone into `_donor_staging/mobilerun` |

### Key Local Finding: Pre-Existing Hermes Agent
`C:\Users\utpal\AppData\Local\hermes\hermes-agent` already contains a complete git checkout of `NousResearch/hermes-agent` with:
- `run_agent.py` (`AIAgent`, streaming loop, hard interrupts)
- `hermes_state.py` and `hermes_state_schema.py` (SQLite WAL schema version 12)
- `agent/context_compressor.py`, `agent/tool_executor.py`, `agent/tool_guardrails.py`
- `cron/scheduler.py`
This provides immediate, offline reference and eliminates any risk of upstream network issues when assimilating Repo #3.

---

## 6. Frontend-Backend Touchpoints & Contract Mapping

### System Network Topology & Ports

```
[ Electron / React UI ]
   ├── Port 5174: Vite Local Dev Server (http://127.0.0.1:5174)
   │
   ├── REST API: http://127.0.0.1:8765 ──────────────┐
   │                                                 ▼
   ├── WebSocket Channels:                           [ backend/main.py ]
   │   ├── ws://127.0.0.1:8765/ws (jarvisBridge)     │ (Unified Core Gateway)
   │   └── ws://127.0.0.1:8765/ws/jarvis (gateway)   │
   │                                                 ├── Port 8001: omnivoice_service (.venv-omnivoice)
   └── Three.js Arc Reactor Visualizer (60 FPS)      ├── Port 8002: omniparser_service (.venv-omniparser)
       (Direct mutable store via jarvisRealtimeRef)  ├── Port 11434: Ollama Daemon
                                                     └── Phone: ADB :5555 / Portal HTTP :8080 / WS :8081
```

### Critical Health Check Contract in `electron/jarvis-service-runtime.ts`
In `electron/jarvis-service-runtime.ts`, lines 134–149:
```typescript
async function healthCheck(baseUrl: string, expectedService: string): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 3_000)
  try {
    const response = await fetch(`${baseUrl}/health`, { signal: controller.signal })
    if (!response.ok) return false
    const body = (await response.json()) as any
    return body?.status === 'healthy' // <-- CRITICAL: MUST BE 'healthy'
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}
```
**Resolution**: `GET /health` in `backend/main.py` must return:
```json
{
  "status": "healthy",
  "service": "jarvis-core-service",
  "engine": "active",
  "voice": "active",
  "vision": "active",
  "mobile": "standby"
}
```
This guarantees the Electron process registers the sidecar as healthy within 30 seconds and proceeds with launching the window.

### Full REST Endpoint Contract Catalog

| Method | Endpoint | Consumed In Frontend | Payload / Response Specification |
| :--- | :--- | :--- | :--- |
| `GET` | `/health`, `/api/health` | `jarvis-service-runtime.ts`, `IndexRoot.tsx` | `{"status": "healthy", "service": "jarvis-core-service", ...}` |
| `GET` | `/api/env` | `src/pages/settings.tsx` | Keys availability (`GEMINI_API_KEY`, `OLLAMA_AVAILABLE`, `WAKE_WORD`) |
| `POST` | `/api/env` | `src/pages/settings.tsx` | Updates `.env` and runtime model settings dynamically |
| `GET` | `/api/system/stats` | `src/pages/dashboard.tsx` | CPU, RAM, Disk, GPU/VRAM, Battery, OS uptime |
| `GET` | `/api/history` | `src/pages/Workspace/` | Default conversation history messages |
| `POST` | `/api/history/clear` | `src/pages/Workspace/` | Clear session transcript |
| `GET` | `/sessions`, `/api/sessions`| `src/lib/gateway-client.ts` | List all sessions from `state_db.py` |
| `GET` | `/sessions/{id}/messages` | `src/lib/gateway-client.ts` | Retrieve transcript for given session |
| `DELETE`| `/sessions/{id}` | `src/lib/gateway-client.ts` | Delete specific session |
| `GET` | `/search` | `src/pages/Workspace/` | FTS5 message search (`messages_fts`) |
| `GET` | `/v1/tools` | `src/pages/Modules/ModulesPage.tsx` | Catalog of 17+ assimilated tool definitions |
| `POST` | `/v1/tools/invoke` | `src/pages/app-store.tsx`, `Modules` | Direct tool invocation (`name`, `arguments`) |
| `GET` | `/v1/core-memory` | `src/pages/notes.tsx` | Query RAG memories & instincts |
| `POST` | `/v1/core-memory` | `src/pages/notes.tsx` | Ingest user notes into SQLite + FAISS |
| `GET` | `/v1/audit` | `src/components/terminal/terminal.tsx`| AgentShield threat audit logs & tool outcomes |
| `GET` | `/v1/permissions` | `src/pages/settings.tsx` | Tool security clearance levels |
| `GET` | `/v1/agents` | `src/pages/Modules/` | Status of subagents (`planner`, `architect`, etc.) |
| `GET` | `/v1/inbox` | `src/pages/task-manager.tsx` | Cron jobs, power alerts, sentry captures, phone SMS |

### Dual WebSocket Channels & Message Schema

`backend/main.py` binds both `@app.websocket("/ws")` and `@app.websocket("/ws/jarvis")`.

#### 1. Inbound Messages (Client -> Backend)
- `user.message`: `{content: string, session_id: string, model?: string, audio_base64?: string}`
- `audio.control`: `{action: 'start_listen' | 'stop_listen' | 'cancel_speech' | 'synthesize', text?: string}`
- `client.command`: `{command: 'system.toggle' | 'vision.mode' | 'hud.*', payload?: any}`
- `voice:stop` / `barge_in`: Immediate TTS cancel and recorder arm
- `reset_abort`: Hard interrupt (`Ctrl+Alt+Backspace` or UI reset) invoking `hermes_brain.request_hard_interrupt()`

#### 2. Outbound Messages (Backend -> Client)
Every broadcast simultaneously emits:
1. **Modern Envelope (`src/shared/protocol.ts`)**:
   ```json
   {
     "type": "agent.state" | "agent.token" | "agent.complete" | "tool.start" | "tool.result" | "system.metrics" | "error",
     "request_id": "uuid",
     "timestamp": "ISO-string",
     "payload": { ... }
   }
   ```
2. **Legacy Bridge Format (`src/services/jarvisBridge.ts`)**:
   ```json
   { "type": "telemetry", "hardware": { ... }, "network": { ... }, "timestamp": 1234567890 }
   { "type": "voice_state", "state": "IDLE" | "LISTENING" | "THINKING" | "SPEAKING", "amplitude": 0.42, "is_speaking": false }
   { "type": "terminal_log", "level": "info" | "warn" | "error" | "critical", "message": "...", "timestamp": 1234567890 }
   { "type": "agent_response", "session_id": "...", "content": "...", "timestamp": 1234567890 }
   ```

---

## 7. Recommended Phased Implementation Plan

Based on our empirical survey findings:

### Phase 1: Voice Preservation & Legacy Clean Wipe
1. Create `_safe_assets/` and copy `backend/audio/assets/jarvis_ref.wav` to `_safe_assets/jarvis_ref.wav`. Verify hash.
2. Delete legacy documentation `.md` files (`README.md`, `.agent/rules/rules.md`, `.antigravity/rules.md`, `docs/*.md`).
3. Delete legacy Python backend files and stubs in `backend/`, `apps/`, `services/`, root `requirements.txt`, `test.cjs`.

### Phase 2: Directory Architecture, Governance Rules & Profiles
1. Create target directories:
   `backend/{agents,memory,skills,core,engine,security,voice/assets,automation,senses,hardware}`
2. Restore `_safe_assets/jarvis_ref.wav` to `backend/voice/assets/jarvis_ref.wav`.
3. Author `.antigravity/rules.md` and `.agent/rules/rules.md` with the 4 Ironclad Laws (UI Immutability, 3-Tier Routing, Single Mic/Cam ownership, ECC Security).
4. Author agent profiles (`planner.md`, `architect.md`, `security_auditor.md`), memory profiles (`SOUL.md`, `USER.md`, `MEMORY.md`), and runtime skill definitions (`desktop_control.md`, etc.).

### Phase 3: 17-Repository Assimilation via `_donor_staging/`
1. Use local cache `C:\Users\utpal\AppData\Local\hermes\hermes-agent` for instant extraction of `hermes-agent` (SessionDB WAL schema 12, AIAgent loop, context compressor, prompt builder, cron scheduler).
2. Shallow-clone remaining donor repositories one by one into `_donor_staging/`, extract functional logic, and immediately delete the donor folder.
3. Apply crucial bug fixes:
   - `Windows-MCP Issue #383`: Exclude Electron HWND in `windows_mcp_bridge.py`.
   - `Agent-S Issue #235`: Exact equality check `if action[0].strip().upper() in ("DONE", "FAIL"):` in `agent_s3_runner.py`.
   - Omnivoice Issue #199: Cache voice clone prompt `.pt` after first synthesis.
4. Implement CPU fallbacks for all neural models (OmniVoice, OmniParser, RealtimeSTT, DeepFace) since the host machine uses Intel UHD Graphics 630.

### Phase 4: Unified FastAPI + Dual WebSocket Gateway
1. Implement `backend/main.py` with port `8765`, supporting `/health` (`status: "healthy"`), 14 REST endpoints, and dual WebSockets (`/ws` and `/ws/jarvis`).
2. Integrate `native_core/jarvis_native_fallback.py` ctypes Win32 power guardian, emergency abort, and fast screen capture.

### Phase 5: Multi-Environment Reconciliation (`uv`) & Documentation
1. Create `scripts/setup-environments.ps1` using `uv` to configure:
   - Primary `.venv` (Python 3.12 / 3.11 core services)
   - `.venv-omnivoice` (isolated port 8001 microservice)
   - `.venv-omniparser` (isolated port 8002 microservice with pinned transformers 4.40.0)
2. Author clean `README.md` and `docs/UNIFIED_ARCHITECTURE.md`.
3. Run end-to-end verification and smoke tests.
