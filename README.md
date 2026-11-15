# J.A.R.V.I.S. Unified Desktop System

> **Autonomous AI Desktop Assistant with Holographic Arc Reactor Visualizer, 17-Repository Architecture, and Sub-32ms Barge-In Voice Control.**

---

## Architectural Flow Diagram

```
+---------------------------------------------------------------------------------+
|                       REACT 19 / ELECTRON HOLOGRAPHIC UI                        |
|   (Dashboard | Workspace | Modules | Apps | Tasks | Notes | Terminal | Settings)   |
|                 Central Holographic Sphere (JARVIS_LIGHTING_CONFIG)             |
+---------------------------------------------------------------------------------+
                                       |
                   HTTP REST & WebSockets (ws://127.0.0.1:8765/ws)
                                       |
+---------------------------------------------------------------------------------+
|               UNIFIED BACKEND GATEWAY (services/backend/app/main.py on Port 8765)  |
+---------------------------------------------------------------------------------+
       |                         |                           |
+--------------+       +-------------------+       +--------------------+
|  AgentShield |       |    HermesBrain    |       | Hardware Profiler  |
|  (Security)  | <---> |  Autonomous Loop  | <---> | & Telemetry Store  |
+--------------+       +-------------------+       +--------------------+
                                 |
         +-----------------------+-----------------------+
         |                       |                       |
+------------------+   +-------------------+   +--------------------+
| SQLite WAL DB    |   | OmniVoice (8001)  |   | OmniParser (8002)  |
| Hybrid RAG (RRF) |   | 24kHz Cloning TTS |   | YOLOv9 + Florence2 |
+------------------+   +-------------------+   +--------------------+
```

---

## Prerequisites
- **Operating System**: Windows 10/11 x64
- **Node.js**: v18.0.0 or higher
- **Python**: v3.12 x64
- **Package Manager**: `uv` (Fast Astral Python package manager)
- **Optional**: NVIDIA CUDA GPU (for accelerated local LLM and Whisper STT)

---

## Installation & Setup

### Step 1: Install Node Dependencies
```powershell
npm install
```

### Step 2: Bootstrap Multi-Environment Python Setup
Execute the automated PowerShell setup script to configure `.venv`, `.venv-omnivoice`, and `.venv-omniparser`:
```powershell
.\scripts\setup-environments.ps1
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys (optional if using local Ollama):
```powershell
Copy-Item .env.example .env
```

### Step 4: Run Development Server
Start the frontend and backend concurrently:
```powershell
npm run dev
```

Or run the backend sidecar independently:
```powershell
node scripts/run-jarvis-service.mjs
```

---

## End-to-End Verification Suite
Run the standard system verification gates:
```powershell
# Run standard verification gates (Frontend, Backend, Boot, Smoke, Packaging)
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1

# Run full 9-row end-to-end integration suite (Phase 2C matrix)
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Full
```

Run the milestone opaque-box test runner:
```powershell
# Run full 4-tier test suite
python services/backend/tests/e2e/runner.py

# Run specific milestone verification
python services/backend/tests/e2e/runner.py --milestone M5

# Run structured JSON reporting
python services/backend/tests/e2e/runner.py --json
```

---

## License
MIT License. All assimilated open-source repositories maintain their respective licenses.
