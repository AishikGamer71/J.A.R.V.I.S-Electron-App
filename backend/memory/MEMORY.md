# Long-Term Factual Memory

## 1. System Topology & Architecture
- **Application Type**: Unified J.A.R.V.I.S. Desktop Electron Application.
- **Gateway Server**: FastAPI running on `127.0.0.1:8765` providing full REST API and WebSocket routes (`/ws`, `/ws/jarvis`).
- **OmniVoice TTS Microservice**: Running on `http://127.0.0.1:8001/tts` inside `.venv-omnivoice`.
- **OmniParser V2 Microservice**: Running on `http://127.0.0.1:8002/parse` inside `.venv-omniparser`.
- **Primary State Database**: SQLite WAL schema version 12 located at `~/.jarvis/state.db`.
- **Homunculus Observations**: Logged continuously to `~/.jarvis/homunculus/observations.jsonl`.
- **Telemetry Store**: Database located at `~/.jarvis/telemetry.db`.
- **Trace Database**: Routing heuristics located at `~/.jarvis/traces.db`.

## 2. Governance Constraints
- The UI React frontend is 100% visually immutable. Central visualizer displays golden-amber holographic sphere (`#000000` background, no upper buttons, no Ultron toggles).
- Windows desktop automation excludes Electron `HWND` to prevent COM UIAutomation deadlock.
- Emergency abort hotkey is hardwired to `Ctrl+Alt+Backspace`.

## 3. Learned Instincts & Workflow Rules
- Initial state: Confidence baseline established. Continuous learning engine updates active rules in `~/.jarvis/homunculus/instincts/personal/`.
- High-confidence rules ($\ge 0.70$) are dynamically incorporated into prompts by `core/prompt_builder.py`.
