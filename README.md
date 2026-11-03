# J.A.R.V.I.S — Polyglot Autonomous AI Desktop Assistant

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Electron](https://img.shields.io/badge/Electron-40-teal.svg)
![React](https://img.shields.io/badge/React-19-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-yellow.svg)
![Rust/Win32](https://img.shields.io/badge/Native%20Core-Rust%20%7C%20Win32%20C--ABI-orange.svg)
![Architecture](https://img.shields.io/badge/Architecture-Polyglot%20Client--Sidecar-purple.svg)

**J.A.R.V.I.S** is a standalone, local-first Windows Electron Desktop Application engineered with high-performance polyglot architecture:
- **TypeScript / TSX (`src/` & `electron/`)**: 100% restored and visually locked original GitHub UI cockpit (React 19 + Three.js particle sphere + HUD telemetry dials + multi-tab workspace + widgets), supervised Electron main process, and typed WebSocket client (`ws://127.0.0.1:8765/ws` and `/ws/jarvis`).
- **Python 3.11 (`backend/`)**: Autonomous AI agent loop, multi-tier neural router (Gemini 2.5 Flash, OpenAI GPT-4o, Ollama), ECC continuous learning memory, Agent-S3 multimodal computer use, and OmniVoice 24kHz zero-shot voice synthesis.
- **Rust & Win32 C-ABI (`native_core/`)**: Low-latency Windows OS control, sub-millisecond charger unplug interrupts, BitBlt screen capture, SendInput execution, and hardware emergency abort (`Ctrl+Alt+Backspace`).

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│               J.A.R.V.I.S ELECTRON DESKTOP APPLICATION SHELL                   │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │   RESTORED ORIGINAL HUD COCKPIT (React 19 + Three.js + Tailwind CSS)   │   │
│   │   • Dashboard: 3D particle sphere, audio visualizer, mini-overlays     │   │
│   │   • Workspace: Multi-tab chat, code workspace, activity feed           │   │
│   │   • Modules: Speech-to-Text, Text-to-Speech, Translator, Digital Docs  │   │
│   │   • Widgets: Leaflet maps, weather, stock tickers, email, camera vision│   │
│   │   • Terminal & Settings: Integrated console, hardware telemetry        │   │
│   └───────────────────────────────────┬────────────────────────────────────┘   │
│                                       │ Typed WebSocket (ws://127.0.0.1:8765/ws)│
│   ┌───────────────────────────────────▼────────────────────────────────────┐   │
│   │   Electron Main Supervisor (`electron/main.ts` / `electron/`)          │   │
│   │   • Supervised Python sidecar lifecycle (`.venv\Scripts\python.exe`)   │   │
│   │   • Clean SIGINT / SIGTERM process tree tree-kill on window exit       │   │
│   │   • Window controls, hardware monitors, PTY terminal IPC channels      │   │
│   └───────────────────────────────────┬────────────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼────────────────────────────────────────┐
│                   PYTHON 3.11 AI, VOICE & AUTOMATION CORE                      │
│   ┌────────────────────────────────────────────────────────────────────────┐   │
│   │   FastAPI Server & WebSocket Hub (`backend/main.py`)                   │   │
│   │   • Bi-directional real-time telemetry, terminal logs, and chat events │   │
│   │   • Dual protocol envelopes (/ws and /ws/jarvis) for seamless parity   │   │
│   ├────────────────────────────────────────────────────────────────────────┤   │
│   │   Core AI Engine & Intelligence (`backend/core/`)                      │   │
│   │   • AIAgent conversation loop with ECC task planner & auto-compaction  │   │
│   │   • ToolRegistry: Self-registering tools with AgentShield validation   │   │
│   │   • Dynamic SKILL.md procedural loader & background cron scheduler     │   │
│   ├────────────────────────────────────────────────────────────────────────┤   │
│   │   Security & Guardrails (`backend/security/agent_shield.py`)           │   │
│   │   • Strict blocklist: destructive shell commands (`rm -rf`, format)    │   │
│   │   • Protected files guard (.env, id_rsa, credentials.json)             │   │
│   │   • Automatic output credential & secret redaction                     │   │
│   ├────────────────────────────────────────────────────────────────────────┤   │
│   │   Autonomous Computer Use (`backend/automation/s3/`)                   │   │
│   │   • Agent-S3 multimodal GUI automation with OSWorldACI grounding       │   │
│   │   • Issue #178 LRU coordinate cache: eliminates redundant OCR re-scans │   │
│   │   • Issue #235/#236 fix: exact token matching prevents premature exit  │   │
│   ├────────────────────────────────────────────────────────────────────────┤   │
│   │   Voice & Audio Pipeline (`backend/audio/`)                            │   │
│   │   • OmniVoice 24kHz zero-shot cloning with British reference audio     │   │
│   │   • 60 FPS RMS amplitude streamer directly bound to ArcReactor/Sphere  │   │
│   │   • Edge-TTS fallback + openWakeWord + instant barge-in interruption   │   │
│   ├────────────────────────────────────────────────────────────────────────┤   │
│   │   Hardware Power Guardian (`backend/hardware/power_guardian.py`)       │   │
│   │   • 1ms charger unplug/plug detector triggering instant voice alert    │   │
│   └───────────────────────────────────┬────────────────────────────────────┘   │
└───────────────────────────────────────┼────────────────────────────────────────┘
                                        │ Direct C-ABI Call
┌───────────────────────────────────────▼────────────────────────────────────────┐
│               RUST & WIN32 NATIVE CORE (`native_core/`)                        │
│   • Compiled PyO3 Extension (`jarvis_native_core.pyd`)                         │
│   • Zero-crash `ctypes.windll` fallback (`jarvis_native_fallback.py`)          │
│   • Win32 GetSystemPowerStatus for sub-millisecond charger state detection     │
│   • BitBlt / DXGI high-speed hardware screen capture                           │
│   • SendInput mouse / keyboard dispatch                                       │
│   • Emergency Abort Hook: `Ctrl + Alt + Backspace` hardware kill-switch        │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Directory Structure

```text
J.A.R.V.I.S-Electron-App/
├── .antigravity/
│   └── rules.md                      # Permanent workspace rules lock
├── src/                              # [100% UNTOUCHED RESTORED GITHUB UI]
│   ├── App.tsx                       # Main cockpit mount
│   ├── IndexRoot.tsx                 # Core UI state, theme, audio, and vision bindings
│   ├── main.tsx                      # React 19 mount point & SystemErrorBoundary
│   ├── assets/
│   │   └── main.css                  # Restored HUD styling (locked via attrib +R)
│   ├── components/                   # Restored common, dashboard, terminal, widgets, workspace
│   ├── layouts/                      # jarvis-layout.tsx & lock-screen.tsx
│   ├── pages/                        # Dashboard, Workspace, Modules, Apps, Tasks, Notes, Settings
│   ├── lib/
│   │   └── gateway-client.ts         # Bi-directional reconnecting WebSocket control plane
│   └── services/
│       ├── jarvisBridge.ts           # Typed WebSocket bridge (ws://127.0.0.1:8765/ws)
│       ├── jarvis-ai-brain.ts        # Chat memory & persistence
│       ├── jarvis-voice-ai.ts        # Web Audio analyzer & voice streaming
│       └── system-info.ts            # System status & metrics
├── electron/                         # [RESTORED GITHUB ELECTRON LAYER]
│   ├── main.ts                       # Electron main process & IPC supervisor
│   ├── preload.ts                    # ContextBridge IPC secure bridge
│   ├── jarvis-service-runtime.ts     # Python sidecar supervisor (.venv/Scripts/python.exe)
│   └── handlers/                     # System info, apps, terminal, AI, and security handlers
├── native_core/                      # [RUST & WIN32 LOW-LEVEL ENGINE]
│   ├── Cargo.toml                    # PyO3 Rust extension configuration
│   ├── src/
│   │   └── lib.rs                    # Win32 Power hook, BitBlt capture, SendInput, KillSwitch
│   ├── jarvis_native_fallback.py     # Direct ctypes.windll Win32 C-ABI wrapper (zero-crash fallback)
│   └── __init__.py                   # Dual-mode loader (compiled Rust or zero-crash ctypes fallback)
├── backend/                          # [PYTHON 3.11 AI, VOICE & AUTOMATION CORE]
│   ├── __init__.py
│   ├── main.py                       # FastAPI server + WebSocket hub (ws://127.0.0.1:8765/ws)
│   ├── config.py                     # Unified .env & hardware profile loader
│   ├── requirements.txt              # Clean, pinned Python 3.11 dependencies
│   ├── core/
│   │   ├── agent_loop.py             # AIAgent conversation loop + credential redaction
│   │   ├── tool_registry.py          # Self-registering tool dispatcher + AgentShield validator
│   │   ├── planner.py                # ECC hierarchical task planner
│   │   ├── context_compressor.py     # Middle-turn context compaction (Resolved / Pending)
│   │   └── skill_and_cron.py         # SKILL.md procedural loader + background cron scheduler
│   ├── engine/
│   │   └── inference_router.py       # Multi-engine router (Gemini 2.5 Flash, OpenAI, Ollama)
│   ├── memory/
│   │   ├── state_store.py            # SQLite WAL SessionDB + FTS5 search + prompt injection detector
│   │   ├── knowledge_rag.py          # Hybrid FTS5 + BM25 Reciprocal Rank Fusion indexer
│   │   └── instinct_learner.py       # ECC continuous-learning-v2 habit & confidence scorer
│   ├── security/
│   │   └── agent_shield.py           # PreToolUse command blocker & secret leak scanner
│   ├── automation/
│   │   ├── desktop_controller.py     # Async Windows GUI runner + Issue #235 fix + abort switch
│   │   └── s3/
│   │       ├── agent_s3.py           # AgentS3 UIAgent planner & reflection loop
│   │       ├── grounding.py          # OSWorldACI + Issue #178 coordinate cache fix
│   │       └── common_utils.py       # Safe LLM invocation & screenshot hashing
│   ├── audio/
│   │   ├── omnivoice_tts.py          # OmniVoice zero-shot cloning + 60 FPS amplitude streamer
│   │   ├── voice_ears.py             # Wake-word detection ("hey jarvis") + barge-in interruption
│   │   └── assets/
│   │       └── jarvis_ref.wav        # British J.A.R.V.I.S reference audio clip
│   ├── hardware/
│   │   └── power_guardian.py         # 1ms charger unplug detector -> instant OmniVoice alert
│   ├── skills/                       # SKILL.md custom capability definitions
│   ├── test_backend.py               # Unit verification test suite
│   └── test_e2e_ws.py                # End-to-end WebSocket & telemetry verification
├── .env.example                      # Template environment variable configuration
├── package.json                      # Workspace scripts and dependencies
└── README.md                         # Documentation
```

---

## ⚡ Key Capabilities & Technical Innovations

### 1. 🛡️ ECC AgentShield & Native Command Blocker
Every tool call, terminal command, and file access passes through a dual-layered security guardrail before execution:
- **Destructive Command Blocking**: Immediate denial of commands matching dangerous patterns (`rm -rf`, `format C:`, disk wiping, recursive deletions).
- **Protected File Access**: Prohibits reading `.env`, private keys (`id_rsa`, `id_ed25519`), or credentials.
- **Output Credential Redaction**: Automatically scrubs API keys (`AIza...`, `sk-...`, `ghp_...`, Bearer tokens) before logs reach the terminal or renderer.

### 2. ⚡ Sub-Millisecond Charger Unplug Interrupt (Power Guardian)
Uses the Win32 `GetSystemPowerStatus` API to poll AC power status. When external power is disconnected:
- An immediate audio vocalization is triggered via OmniVoice: *"Sir, external power has been disconnected. Running on internal battery at [X] percent."*
- Telemetry dials in the frontend update in real time with an alert border.

### 3. 🛑 Emergency Hardware Kill-Switch (`Ctrl + Alt + Backspace`)
During autonomous GUI automation (computer-use):
- Low-level asynchronous key polling runs every loop iteration via `GetAsyncKeyState`.
- Pressing `Ctrl + Alt + Backspace` immediately halts all mouse, keyboard, and agent execution, latches an emergency abort state, and broadcasts an alert to the user.

### 4. 🖱️ Agent-S3 Computer-Use with Upstream Bug Fixes
- **Issue #178 LRU Coordinate Cache**: Remembers previously grounded UI bounding boxes to avoid expensive full-screen VLM inference during sequential button interactions.
- **Issue #235 / #236 Exact Token Matching**: Fixes the critical bug where casual assistant phrasing like *"Well done"* triggered premature agent termination. Tasks now only conclude upon receiving explicit formatted termination tokens (`DONE(...)` or `FAIL(...)`).

### 5. 🎙️ 60 FPS Particle Sphere Audio Streaming
- OmniVoice and Edge-TTS voice streams compute real-time RMS amplitude frames.
- WebSocket sends amplitude updates throttled via `requestAnimationFrame` on the client, driving the 3D Three.js particle sphere dynamics with zero React re-render overhead.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js**: `v20.19.0+` or `v22.12.0+`
- **Python**: `3.11.x` (`3.11.9` recommended)
- **Git**: Installed and on `PATH`
- **Windows OS**: Windows 10 or 11 (64-bit)

---

### Step 1: Environment Setup

Clone the repository and enter the directory:
```powershell
git clone https://github.com/AishikGamer71/J.A.R.V.I.S-Electron-App.git
cd J.A.R.V.I.S-Electron-App
```

Create a Python 3.11 virtual environment and install backend dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
```

Install frontend Node dependencies:
```powershell
npm install
```

Configure your API keys:
```powershell
cp .env.example .env
```
Edit `.env` and set your `GEMINI_API_KEY` (or configure OpenAI / Ollama).

---

### Step 2: Verification Tests

Run the full backend unit test suite:
```powershell
npm run test:backend
```

Run the live end-to-end WebSocket & telemetry verification:
```powershell
npm run test:backend:e2e
```

Build the production bundles (Vite renderer + Electron main process):
```powershell
npm run build
```

---

### Step 3: Launching the Application

Start J.A.R.V.I.S in development mode with live HMR:
```powershell
npm run dev
```

Start the packaged / production build:
```powershell
npm run start
```

---

## 🎮 Cockpit Controls & Hotkeys

| Action | Control / Hotkey | Description |
| :--- | :--- | :--- |
| **Send Query** | `Enter` or Send Button | Sends user prompt to the autonomous agent loop |
| **Barge-in / Stop Speech** | Mic Button or Stop Button | Instantly halts active voice synthesis and returns to idle |
| **Emergency Abort** | `Ctrl + Alt + Backspace` | Hardware-level kill-switch that halts all autonomous GUI actions |
| **Fullscreen Toggle** | `F11` | Toggles fullscreen mode for the Electron window |
| **Window Minimize** | Minimize HUD Button | Minimizes the Electron window |
| **Window Close** | Close HUD Button | Shuts down frontend, Python supervisor, and background threads cleanly |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Developed with polyglot precision for the **J.A.R.V.I.S Desktop AI** ecosystem.
