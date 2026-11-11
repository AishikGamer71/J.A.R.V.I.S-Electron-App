# PERMANENT WORKSPACE GOVERNANCE & IRONCLAD LAWS — J.A.R.V.I.S. UNIFIED SYSTEM

## APPLICATION SCOPE & GOVERNANCE: DESKTOP APPLICATION ONLY

J.A.R.V.I.S. is strictly a unified DESKTOP APPLICATION ONLY. All backend assimilation, automation services, camera/mic sensory pipelines, and UI features are exclusively engineered for the local Windows desktop environment. No mobile or web application conversions are permitted.

## LAW 1: PURE J.A.R.V.I.S. HOLOGRAPHIC SPHERE UI & STRICT IMMUTABILITY

1. **ZERO UI DRIFT & Source of Truth (DESKTOP APPLICATION ONLY)**:
   The existing React 19 / TypeScript / Electron frontend restored from https://github.com/AishikGamer71/J.A.R.V.I.S-Electron-App.git is the absolute visual source of truth. J.A.R.V.I.S. operates strictly as a DESKTOP APPLICATION ONLY. Under no circumstances may an agent delete, rename, move, restyle, or alter existing layout grids, Tailwind/CSS classes, SVGs, buttons, or typography outside of authorized visualizer tuning.
2. **Locked Visual Files**:
   The following files and directories are permanently locked against structural or visual modifications:
   - `index.html`
   - `src/main.tsx`, `src/App.tsx`, `src/IndexRoot.tsx`
   - `src/env.d.ts`, `src/global.d.ts`
   - `src/layouts/jarvis-layout.tsx` (All 9 navigation tabs: `DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`; all system control bar buttons: `toggleSystem`, `toggleMic`, `toggleVideo`, `startVision('camera')`, `startVision('screen')`, source modal, and `LiveClock` must remain visually intact)
   - `src/components/common/**`, `src/components/dashboard/**`
   - `src/components/widgets/email-widget.tsx`, `image-widget.tsx`, `map-view.tsx`, `stock-widget.tsx`, `weather-widget.tsx`, `wormhole.tsx`
   - `public/**` and `assets/**`
   - Build configurations: `components.json`, `vite.config.ts`, `tsconfig*.json`, `electron-builder.yml`
3. **Authorized Visual Modifications Only**:
   - In `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts`, completely strip all upper buttons, top toolbar controls, and Ultron theme/mode/persona controls. The central visualizer displays ONLY the canonical golden-amber J.A.R.V.I.S. holographic neural sphere on `#000000` background.
   - Calibrate holographic lighting in `src/components/widgets/arc-reactor.tsx` using `JARVIS_LIGHTING_CONFIG` (outer dark bronze ring `rgba(78, 44, 15, 0.55)`, golden neural clusters `rgba(218, 160, 42, 0.76)`, radial filaments `rgba(242, 188, 62, 0.68)`, warm silver-gold inner core ring `rgba(225, 215, 190, 0.62)`).
   - Drive rotations, filament pulses, and audio FFT reactivity via frame-rate-independent delta time with exponential smoothing (`smoothing = 1 - Math.exp(-10 * dt)`).
4. **Allowed Bridge Wiring Files**:
   Non-visual data binding and protocol bridges may be updated exclusively in:
   - `src/shared/protocol.ts`
   - `src/services/jarvisBridge.ts`
   - `src/lib/gateway-client.ts`
   - `src/services/jarvis-ai-brain.ts`, `jarvis-voice-ai.ts`, `system-info.ts`, `hermes-adapter.ts`
   - `electron/main.ts`, `preload.ts`, `backend-command.ts`, `backend-child.ts`, `backend-health.ts`, `backend-ready.ts`
   - `scripts/run-jarvis-service.mjs`, `package.json`

## LAW 2: 3-TIER ACTION ROUTING STRATEGY

Every autonomous action performed by the agent must select the lowest-friction, non-intrusive automation tier:

1. **Tier 1 — Web Browsing & Information Extraction**:
   - Remote browsing, form filling, shopping, and web logins must route to `browser_use_runner.py` via background Chrome DevTools Protocol (`CDP`).
   - Fast URL content scraping and research report compilation must route to `crawl4ai_service.py` and `gpt_researcher_service.py`.
   - **Rule**: Never hijack or move the physical mouse cursor for web operations.
2. **Tier 2 — Document Reading & Conversion**:
   - Local PDF, DOCX, XLSX, PPTX, audio, images, and YouTube URLs must route to `markitdown_service.py`.
   - OCR is automatically executed on embedded images with table structure preservation and `<sheetView showZeroes>` XML repair.
3. **Tier 3 — Native Windows OS & Desktop Automation**:
   - Native Windows UI interactions must route first to `windows_mcp_bridge.py` using native COM UIAutomation tree (<10ms execution).
   - **Critical Deadlock Guard**: `windows_mcp_bridge.py` MUST explicitly exclude any `HWND` belonging to the `J.A.R.V.I.S-Electron-App` process tree (`electron.exe` or window title matching "JARVIS") to prevent UI deadlocks.
   - Escalate to `omniparser_service.py` (YOLOv9-E + Florence-2 icon detection on port 8002) + `agent_s3_runner.py` (Agent-S3 `OSWorldACI`) ONLY for custom canvas, DirectX/OpenGL surfaces, or unlabelled graphical icons.
   - Always verify exact termination string `action[0].strip().upper() in ("DONE", "FAIL")` before running desktop actions.
4. **Mobile Device Extension**:
   - Android smartphone tasks route to `mobilerun_service.py` via wireless ADB (`:5555`) or Portal HTTP (`:8080`) and WebSocket (`:8081`).

## LAW 3: EXCLUSIVE HARDWARE DEVICE OWNERSHIP (SINGLE CAMERA & SINGLE MIC)

Hardware contention across multiple processes or threads will destabilize the application. Hardware ownership is strictly exclusive:

1. **Webcam (Optical Senses)**:
   - `cv2.VideoCapture(0)` is exclusively opened and managed by `backend/senses/camera_hub.py` using a Single-Producer Multi-Consumer (SPMC) ring buffer.
   - Feeds contiguous 60 FPS RGB frames directly to `backend/senses/mediapipe_gestures.py` in async `RunningMode.LIVE_STREAM`.
   - Copies a thread-safe 2 Hz BGR frame to `backend/senses/deepface_sentry.py` (Facenet512 + YuNet + FasNet anti-spoofing).
   - No other script, thread, or donor library may instantiate OpenCV camera handles.
2. **Microphone (Audio Senses)**:
   - 16kHz mono PCM microphone stream is exclusively opened and owned by `backend/voice/realtime_stt.py` (`AudioToTextRecorder` with `openWakeWord` `hey_jarvis_v0.1.onnx`, Silero VAD, WebRTC VAD, and `faster-whisper-large-v3-turbo-ct2`).
3. **Sub-32ms Barge-In Voice Interruption**:
   - On `on_vad_start` or `on_recording_start`, `voice/audio_pipeline.py` immediately asserts `tts_stop_event.set()`, invokes `sounddevice.stop()`, interrupts 24kHz `OmniVoice` synthesis, and broadcasts `agent.state: listening` over WebSocket.

## LAW 4: ECC CONTINUOUS LEARNING & AGENTSHIELD SECURITY

1. **Pre/Post Tool Execution Hooks**:
   - Every tool call dispatched by `core/tool_dispatcher.py` must pass through `security/ecc_hooks.py`.
   - `pre_tool_use`: Calls `security/agent_shield.py` to validate arguments against 14 secret patterns, destructive shell commands (`rm -rf /`, `format`, `del /f /s /q`, registry alteration), config file protection, and prompt injection attacks.
   - `post_tool_use`: Logs JSON-serialized execution metadata (`timestamp`, `session_id`, `tool_name`, `args`, `status`, `duration_ms`) to `~/.jarvis/homunculus/observations.jsonl`.
2. **Instinct Continuous Learning Engine**:
   - `memory/instinct_engine.py` continuously mines observations from `observations.jsonl`.
   - Maintains atomic YAML instinct files in `~/.jarvis/homunculus/instincts/personal/`.
   - Dynamically injects all learned instincts with confidence $\ge 0.70$ into the LLM system prompt via `core/prompt_builder.py`.
3. **Emergency Hardware Abort Hotkey**:
   - Pressing `Ctrl+Alt+Backspace` immediately halts all desktop computer-use, mouse movements, keyboard typing, and running agent loops in under 1 millisecond.
4. **Power & Battery Guardian**:
   - `hardware/power_guardian.py` polls Win32 `GetSystemPowerStatus` every 50ms. Transitions in AC power or battery thresholds ($\le 20\%$, $\le 10\%$) immediately trigger voice notifications and HUD metric updates.
