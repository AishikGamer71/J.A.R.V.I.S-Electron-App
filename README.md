# J.A.R.V.I.S — Autonomous AI Desktop Assistant

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Electron](https://img.shields.io/badge/Electron-40-teal.svg)
![React](https://img.shields.io/badge/React-19-blue.svg)
![Powered by](https://img.shields.io/badge/Runtime-Nous%20Hermes%20Agent-purple.svg)

**J.A.R.V.I.S** is a futuristic, local-first autonomous AI desktop assistant. It brings together an interactive 3D particle HUD, voice synthesis and wake-word detection, customizable tool execution, and system automations—powered natively by [Nous Research's Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime.

---

## 🧠 Architecture Overview

J.A.R.V.I.S uses a clean desktop client-to-engine architecture:

```
┌────────────────────────────────────────────────────────┐
│               J.A.R.V.I.S Electron Shell               │
│   ┌────────────────────────────────────────────────┐   │
│   │    React 19 + Three.js Particle HUD Interface  │   │
│   │    Audio Visualizer + Dynamic Voice States     │   │
│   │    Automation Modals & Custom Tool Controls    │   │
│   └──────────────────────┬─────────────────────────┘   │
│                          │ ContextBridge IPC           │
│   ┌──────────────────────▼─────────────────────────┐   │
│   │      Electron Main Process & IPC Supervisor    │   │
│   └──────────────────────┬─────────────────────────┘   │
└──────────────────────────┼─────────────────────────────┘
                           │ Local WebSocket / REST Gateway
┌──────────────────────────▼─────────────────────────────┐
│             Nous Research Hermes Agent Engine          │
│   ┌────────────────────────────────────────────────┐   │
│   │  Local CLI / Headless Gateway (`hermes serve`) │   │
│   │  Multi-Tier Model Routing (Ollama / Cloud LLM) │   │
│   │  Autonomous Subagents, Skills & MCP Support    │   │
│   │  Persistent Memory Bank & Session Storage      │   │
│   └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### Core Components

1. **Desktop Shell (`apps/desktop` / `src` / `electron`)**:
   - Built on Electron 40, React 19, Vite, Tailwind CSS, and Three.js.
   - Houses the voice HUD, visualizer, widgets, and system automation IPC handlers.
   - Connects to the Hermes gateway via `src/services/hermes-adapter.ts` and `window.hermesDesktop`.

2. **Underlying Intelligence (`Hermes Agent`)**:
   - Upstream autonomous agent runtime by [Nous Research](https://github.com/NousResearch/hermes-agent).
   - Manages model invocation (local Ollama or cloud providers), tool dispatch, memory banks, subagents, and sessions.

3. **Voice Engine (`services/voice-service`)**:
   - Audio microservice featuring `faster-whisper` for speech-to-text, `Piper` for neural text-to-speech, `openWakeWord` for wake word activation, and `EchoGate` for acoustic feedback prevention.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js**: `v20.19.0+` or `v22.12.0+`
- **Python**: `3.10+`
- **Git**: Installed and available in your `PATH`
- **Local LLM (Optional but recommended)**: [Ollama](https://ollama.ai) running locally (`http://127.0.0.1:11434`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AishikGamer71/J.A.R.V.I.S-Electron-App.git
   cd J.A.R.V.I.S-Electron-App
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build and stamp native bundles:
   ```bash
   npm run build
   ```

4. Start in development mode:
   ```bash
   npm run dev
   ```
   This starts the Vite renderer server on `http://127.0.0.1:5174` and launches the Electron application with live Hermes backend connectivity.

---

## 🛠️ Configuration & Models

J.A.R.V.I.S automatically uses your local Hermes configuration located at:
- **Windows**: `%LOCALAPPDATA%\hermes` (or `~/.hermes`)
- **macOS / Linux**: `~/.hermes`

To configure model providers and fallback chains:
```bash
# Select default model (e.g., Ollama local model or cloud provider)
hermes model

# Configure cloud API keys (Gemini, Groq, Anthropic, OpenAI)
hermes setup
```

---

## 📜 Credits & Attribution

- Built on the open-source **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** runtime by **Nous Research** (licensed under MIT).
- Developed and maintained by **AishikGamer71** and the **J.A.R.V.I.S AI Team**.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
