# J.A.R.V.I.S. Project Rules

## Scope

J.A.R.V.I.S. is a **Windows desktop application only**. Electron + React 19 frontend, Python FastAPI sidecar backend. No mobile or web conversions.

## Architecture

- **Frontend**: React 19 / TypeScript / Electron in `apps/desktop/`. 9 navigation tabs. Central holographic neural sphere visualizer.
- **Backend**: Python FastAPI in `services/backend/app/` on `127.0.0.1:8765`. REST + dual WebSocket (`/ws`, `/ws/jarvis`).
- **Runtime data**: `%APPDATA%\JARVIS\` (dev fallback `.data/`, gitignored) — memory, logs, models live outside the repo.
- **Persona files**: Product files in `config/persona/`, not dev skills — stay out of `.agents/`.

## Locked Files — Do Not Modify Structure Or Visuals

- `apps/desktop/index.html`, `apps/desktop/src/main.tsx`, `apps/desktop/src/App.tsx`, `apps/desktop/src/IndexRoot.tsx`
- `apps/desktop/src/layouts/jarvis-layout.tsx` (9 tabs + system control bar)
- `apps/desktop/src/components/common/**`, `apps/desktop/src/components/dashboard/**`
- `apps/desktop/src/components/widgets/email-widget.tsx`, `image-widget.tsx`, `map-view.tsx`, `stock-widget.tsx`, `weather-widget.tsx`, `wormhole.tsx`
- `apps/desktop/public/**`, `apps/desktop/assets/**`
- Build configs: `apps/desktop/components.json`, `apps/desktop/vite.config.ts`, `apps/desktop/tsconfig*.json`, `electron-builder.yml`

## Allowed Edits

**Visual tuning only in**:
- `apps/desktop/src/components/widgets/arc-reactor.tsx` — holographic lighting via `JARVIS_LIGHTING_CONFIG`
- `apps/desktop/src/services/theme-manager.ts` — theme state

**Bridge wiring**:
- `apps/desktop/src/shared/protocol.ts`, `apps/desktop/src/services/jarvisBridge.ts`, `apps/desktop/src/lib/gateway-client.ts`
- `apps/desktop/src/services/jarvis-ai-brain.ts`, `jarvis-voice-ai.ts`, `system-info.ts`, `hermes-adapter.ts`
- `apps/desktop/electron/main.ts`, `preload.ts`, `backend-command.ts`, `backend-child.ts`, `backend-health.ts`, `backend-ready.ts`
- `scripts/run-jarvis-service.mjs`, `package.json`

## 3-Tier Action Routing

1. **Web browsing** -> `browser_use_runner.py` (CDP). Never move the physical mouse.
2. **Document reading** -> `markitdown_service.py` (PDF, DOCX, XLSX -> Markdown + OCR).
3. **Windows OS automation** -> `windows_mcp_bridge.py` (COM UIAutomation). Must exclude Electron HWND to prevent deadlocks. Escalate to OmniParser + Agent-S3 only for unlabelled graphical icons.

## Hardware Ownership

- **Camera**: Exclusively `camera_hub.py` (SPMC ring buffer -> MediaPipe gestures + DeepFace).
- **Microphone**: Exclusively `realtime_stt.py` (openWakeWord + faster-whisper).
- No other script may open camera or mic handles.

## Security

- Every tool call passes through `security/ecc_hooks.py` pre/post hooks.
- `agent_shield.py` validates against 14 secret patterns and destructive commands.
- Emergency abort: `Ctrl+Alt+Backspace` halts all desktop automation immediately.

## Backend Services

| Port | Service | Purpose |
|------|---------|---------|
| 8765 | FastAPI gateway | REST + WebSocket |
| 8001 | OmniVoice | 24kHz TTS microservice |
| 8002 | OmniParser | YOLOv9-E icon detection |

## Testing

- E2E tests use Playwright (`apps/desktop/playwright.config.ts`)
- Python tests use pytest (`services/backend/tests/`)
- Run tests before committing. Always.
