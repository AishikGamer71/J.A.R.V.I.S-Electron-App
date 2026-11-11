# Frontend & UI Architecture Audit Report

**Date:** 2026-11-10T08:15:00Z  
**Auditor:** `explorer_survey_2` (UI & Frontend Auditor)  
**Workspace:** `e:\Projects\J.A.R.V.I.S Electron App`  
**Reference Document:** `c:\Users\utpal\Downloads\jarvis_antigravity_master_prompt.md` & `ORIGINAL_REQUEST.md`

---

## 1. Executive Summary

This comprehensive audit investigates the existing React/TypeScript/Electron frontend of the J.A.R.V.I.S. Desktop Application. The objective is to verify UI structure, components, navigation tabs, control bars, visualizers, animation physics, themes, and backend communication bridges against the requirements outlined in R1 and Phase 0/Law 1.

### Key Audit Findings:
1. **Central Visualizer & `arc-reactor.tsx` vs `sphere.tsx`**:
   - `src/components/widgets/arc-reactor.tsx` is **not currently present** on the filesystem.
   - The central 3D visualizer is currently implemented in `src/components/dashboard/sphere.tsx` and imported into `src/pages/dashboard.tsx` as `<Sphere />`.
   - `src/components/dashboard/sphere.tsx` utilizes `@react-three/fiber` (Three.js) rendering a 2,600-particle Fibonacci sphere with gyroscopic rings, volumetric glow sprite, and state-based morphing (Fibonacci sphere, holographic globe, and beveled cube).
   - In `jarvis_antigravity_master_prompt.md` (Section 6.6), `src/components/widgets/arc-reactor.tsx` is specified as the target component housing `JARVIS_LIGHTING_CONFIG` (balanced golden-amber palette, dark bronze outer ring, warm silver-gold inner core) and delta-time animation physics with exponential damping.
2. **Ultron Controls & Upper Buttons Status**:
   - Neither `src/layouts/jarvis-layout.tsx` nor `src/services/theme-manager.ts` currently contain any Ultron persona, mode switcher, or red/crimson Ultron theme presets.
   - The top toolbar in `src/layouts/jarvis-layout.tsx` contains clean navigation tabs, the Neural Interface header, the System Online/Standby toggle, and `LiveClock`.
   - In `src/pages/dashboard.tsx`, there is a "Focus Mode" button at the top of the center column, a mobile video preview box at the top right, and the bottom control pill dock (`onVisionClick`, `toggleSystem`, `toggleMic`).
3. **9 Navigation Tabs Verification**:
   - All 9 core navigation tabs are implemented and wired in `src/config/navigation.tsx` and `src/layouts/jarvis-layout.tsx`:
     1. `DASHBOARD` -> `src/pages/dashboard.tsx`
     2. `WORKSPACE` (mapped to `CHAT` in navigation config) -> `src/pages/Workspace/WorkspaceContainer.tsx`
     3. `MODULES` -> `src/pages/Modules/ModulesPage.tsx`
     4. `APPS` (mapped to `Apps` in navigation config) -> `src/pages/app-store.tsx`
     5. `TASKS` (mapped to `TASK MANAGER` in navigation config) -> `src/pages/task-manager.tsx`
     6. `NOTES` -> `src/pages/notes.tsx`
     7. `GALLERY` -> `src/pages/gallery.tsx`
     8. `TERMINAL` -> `src/components/terminal/terminal.tsx`
     9. `SETTINGS` -> `src/pages/settings.tsx`
     *(Plus `PHONE` -> `src/pages/phone.tsx`)*
4. **Theme System (`src/services/theme-manager.ts`)**:
   - Presets defined: `emerald` (JARVIS Matrix, `#10b981`), `sarvam-ai` (`#e67e22`), and `midnight-frost` (`#e2e8f0`).
   - CSS variables applied to document root (`--theme-primary`, `--theme-secondary`, `--theme-bg`, `--theme-surface`, `--theme-border`, `--theme-glow`, `--theme-blur`).
5. **WebSocket & REST Client Bridges**:
   - `src/lib/gateway-client.ts`: Connects to `http://127.0.0.1:8765` and `ws://127.0.0.1:8765/ws/jarvis`.
   - `src/services/jarvisBridge.ts`: Connects to `ws://127.0.0.1:8765/ws` and feeds `jarvisRealtimeRef` mutable store (zero React re-renders) at 60 FPS for Three.js animations.
   - `src/services/jarvis-voice-ai.ts`: Manages Web Audio `AudioContext` and `AnalyserNode` connected to microphone stream.

---

## 2. File-by-File Inspection

### 2.1 Visualizer & Reactor: `src/components/widgets/arc-reactor.tsx` & `src/components/dashboard/sphere.tsx`

#### Status of `src/components/widgets/arc-reactor.tsx`
- **File Exists:** No. (Path `src/components/widgets/arc-reactor.tsx` does not exist on disk).
- **Files in `src/components/widgets/`:**
  - `email-widget.tsx` (9,983 bytes)
  - `image-widget.tsx` (5,192 bytes)
  - `map-view.tsx` (4,619 bytes)
  - `stock-widget.tsx` (6,749 bytes)
  - `weather-widget.tsx` (6,074 bytes)
  - `wormhole.tsx` (3,946 bytes)

#### Existing Visualizer: `src/components/dashboard/sphere.tsx`
- **Implementation:** React 19 component using `@react-three/fiber` (`Canvas`, `useFrame`) and `three` (r180).
- **Particle Count:** Default `2600` points in a Fibonacci sphere distribution (`BASE_RADIUS = 1.72`).
- **Layers:**
  1. *Layer 0 (Sprite):* Dark contrast halo (`backdropTexture` generated procedurally via radial gradient canvas).
  2. *Layer 1 (Sprite):* Volumetric inner energy core (`glowTexture` sprite with `AdditiveBlending`).
  3. *Layer 2 (Mesh Torus):* Gyroscopic & scanner rings (Ring 1 at radius 2.06, Ring 2 at radius 2.19, Ring 3 scanner slice ring at radius 1.74).
  4. *Layer 3 (Points):* 3D Morphing particle cloud with position and vertex color buffers.
- **States Supported:**
  `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`.
- **Target Morph Shapes:**
  - `WEB_SEARCH`: Morph to 3D wireframe hologram globe (latitudes & longitudes).
  - `CODING`: Morph to 3D beveled holo-cube.
- **Physics and Animation Loop:**
  - `useFrame((state, delta) => ...)`:
    - Delta-time calculation: `const dt = Math.min(0.05, delta)` (frame-rate independent).
    - Damping factors: `const damp = 1 - Math.exp(-6.2 * dt)` and `const audioDamp = 1 - Math.exp(-14 * dt)` (exponential damping).
    - Audio reactivity: reads from `jarvisService.analyser` (Web Audio API FFT byte frequency data) and `jarvisRealtimeRef.audioLevel` from WebSocket bridge.
    - Fallback synthetic speech cadence: activates when `active === 'SPEAKING' && totalRaw < 0.03` using multi-frequency sine wave modulation.
- **Master Prompt Requirements for `arc-reactor.tsx` (Section 6.6):**
  When implemented/restored, the specification requires:
  ```typescript
  export const JARVIS_LIGHTING_CONFIG = {
    background: '#000000',
    outerRingColor: 'rgba(78, 44, 15, 0.55)',       // Subtle dark bronze outer containment arc
    outerRingGapRadians: [Math.PI * 1.48, Math.PI * 1.66], // Top-right architectural gap
    circuitClusterColor: 'rgba(218, 160, 42, 0.76)', // Mid-tone golden neural matrix
    radialFilamentColor: 'rgba(242, 188, 62, 0.68)', // Balanced golden radial spikes & rays
    innerCoreRingColor: 'rgba(225, 215, 190, 0.62)', // Warm silver-gold inner core ring
    maxShadowBlur: 8,                                // Capped glow preventing clipping
    shadowColor: 'rgba(218, 160, 42, 0.32)',
    baseOpacity: 0.75,
    maxAudioBoostOpacity: 0.92,
  } as const;
  ```

---

### 2.2 Layout & Navigation: `src/layouts/jarvis-layout.tsx`

- **Root Structure:**
  - Full-screen container with flex-column layout.
  - Top Navigation Bar (height `h-14` = 56px, backdrop blur, `border-b border-white/5`).
  - Central View Area (`flex-1 overflow-hidden relative`) wrapping tab transitions with `AnimatePresence`.
  - Source Uplink Modal (`showSourceModal`) for camera vs screen vision selection.
  - Modal mount point (`<ConfirmationModal />`).
- **Top Bar Elements:**
  - *Left section:* Pulse icon `<RiShieldFlashLine />` + "JARVIS AI NEURAL INTERFACE" title.
  - *Center section:* Tabs mapped from `NAVIGATION_MODULES` (with active tab indicator animated via `motion.div` with spring physics).
  - *Right section:*
    - System Online / Standby Toggle button (`props.toggleSystem`): shows pinging status indicator dot and label `"SYSTEM ONLINE"` / `"SYSTEM STANDBY"`.
    - Isolated Clock component: `<LiveClock />` updates at 1 Hz independently without re-rendering parent layout.
- **Ultron Controls:**
  - Checked: **Zero** Ultron controls, toggle switches, or Ultron persona buttons exist in `jarvis-layout.tsx`.
- **Top Toolbar Buttons:**
  - There are no superfluous upper toolbar button clusters in `jarvis-layout.tsx`. The controls are strictly the navigation tab buttons, system status toggle, and clock.

---

### 2.3 Dashboard View: `src/pages/dashboard.tsx`

- **Layout Structure (3-column HUD on `lg` screens):**
  - **Left Column (width 3 cols):**
    - Neural Core Settings Card (`h-70`): Compute mode selector (`local`, `cloud`, `adaptive`), active model dropdown (`CustomSelect`), reasoning effort dropdown.
    - Network Telemetry Panel (`NetworkTelemetryPanel`, `h-32`): Displays WSS latency (`networkStats.ping`), packet rate (`networkStats.rate`), routing status (`GLOBAL` vs `LOCAL`).
    - Core Metrics Panel (`CoreMetricsPanel`): CPU, RAM, and system stats.
  - **Center Column (width 6 cols, visualizer core):**
    - Top Focus Mode Button: `<motion.button ... onClick={() => setIsFocusMode(true)}>Focus</motion.button>`.
    - Mobile Video Preview (visible when `isVideoOn` is true).
    - Central Visualizer: `<div className="w-[60vh] h-[60vh] ..."><Sphere /></div>`.
    - Floating Bottom Pill Dock:
      - Vision toggle button: `<RiCameraLine />` / `<RiSwapBoxLine />` calling `onVisionClick()`.
      - System power toggle: Center circular button with `<RiPhoneFill />` calling `toggleSystem()`.
      - Mic toggle button: `<RiMicLine />` / `<RiMicOffLine />` calling `toggleMic()`.
  - **Right Column (width 3 cols):**
    - Live Transcript & Chat History panel (`TRANSCRIPT` / `LIVE-LOG`).
    - Active Tool Indicator (e.g. `TOOL: <name>` with phase `start`/`result`).
    - Chat message stream with markdown formatting (`ReactMarkdown`, `remarkGfm`) and copy buttons.
    - File attachment and message input form (`chatInput` sending to `gatewayClient.sendChat`).
  - **Focus Mode Overlay:**
    - Triggered by `isFocusMode = true` or `F11` key.
    - Displays full-screen black canvas (`#020611`) with `<Sphere />` scaled up to `84vmin` and a single "EXIT FOCUS (ESC)" button at top-right.

---

### 2.4 Theme Manager: `src/services/theme-manager.ts`

- **Presets Defined:**
  1. `emerald`: JARVIS Matrix (Emerald Protocol) — primary `#10b981`, secondary `#06b6d4`, background `#050505`.
  2. `sarvam-ai`: Sarvam AI — primary `#e67e22`, secondary `#3498db`, background `#0a0a0f`.
  3. `midnight-frost`: Midnight Frost — primary `#e2e8f0`, secondary `#64748b`, background `#000000`.
- **Default Preset:** `DEFAULT_THEME_SETTINGS` points to `emerald`.
- **Ultron Controls & Themes:**
  - Audited: **No Ultron presets** exist in `PRESET_THEMES`.
  - The type definition `ThemePresetId` is strictly `'emerald' | 'sarvam-ai' | 'midnight-frost' | 'custom'`.
- **DOM Integration:**
  - `applyThemeToDom(theme: ThemeSettings)` sets root CSS properties:
    `--theme-primary`, `--theme-primary-hover`, `--theme-secondary`, `--theme-bg`, `--theme-surface`, `--theme-border`, `--theme-glow`, `--theme-blur`.
    Sets `document.body.style.backgroundColor = bg`.

---

## 3. Verification of All 9 Navigation Tabs

The system implements 9 core navigation tabs (plus 1 auxiliary Phone tab) defined in `src/config/navigation.tsx` and dynamically rendered in `src/layouts/jarvis-layout.tsx`:

| Tab ID in UI | Config ID | Underlying Source Component | Verified Functionality |
| :--- | :--- | :--- | :--- |
| **DASHBOARD** | `DASHBOARD` | `src/pages/dashboard.tsx` | Central HUD with `<Sphere />`, telemetry gauges, model/compute mode selectors, live chat transcript, bottom dock controls. |
| **WORKSPACE** | `CHAT` | `src/pages/Workspace/WorkspaceContainer.tsx` | Hosts 3 modes: `NormalChatWorkspace` (general dialogue), `CodeWorkspace` (code editor & file explorer), `CoworkWorkspace` (collaborative agent tasks). |
| **MODULES** | `MODULES` | `src/pages/Modules/ModulesPage.tsx` | Hosts 4 neural subsystems: `TextToSpeechModule`, `SpeechToTextModule`, `TranslatorModule`, `DigitalDocsModule`. |
| **APPS** | `Apps` | `src/pages/app-store.tsx` | Grid of installed desktop applications (`getAllApps()`) with launch capability via `open-app` IPC channel. |
| **TASKS** | `TASK MANAGER` | `src/pages/task-manager.tsx` | High-performance process manager using `react-virtuoso` with CPU/RAM heatmaps, parent/child process trees, and kill process triggers. |
| **NOTES** | `NOTES` | `src/pages/notes.tsx` | Markdown notes manager with create, edit, delete, preview, and storage persistence (`get-notes`). |
| **GALLERY** | `GALLERY` | `src/pages/gallery.tsx` | Media gallery displaying generated images, sentry logs, and screenshots (`get-gallery`, `delete-image`, `open-image-location`). |
| **TERMINAL** | `TERMINAL` | `src/components/terminal/terminal.tsx` | Multi-tab xterm.js terminal emulator with `@xterm/addon-fit`, spawning backend shells via `terminal-spawn`. |
| **SETTINGS** | `SETTINGS` | `src/pages/settings.tsx` | 8-tab configuration center: General, Appearance (theme presets, custom colors, glass blur), AI parameters, Behaviors, API Keys, Permissions, Security, About. |
| *(PHONE)* | `PHONE` | `src/pages/phone.tsx` | Mobile device bridge for wireless ADB, notifications, and screen mirroring. |

---

## 4. System Control Bar Buttons & Triggers

All system controls in `src/layouts/jarvis-layout.tsx` and `src/pages/dashboard.tsx` map directly to bridge and IPC actions:

| Control Button | Location | State / Action | Underlying Dispatch |
| :--- | :--- | :--- | :--- |
| **System Power Toggle** | `jarvis-layout.tsx` (top right) & `dashboard.tsx` (bottom dock) | `isSystemActive` (toggle between Online and Standby) | `toggleSystem()`: In `IndexRoot.tsx`, calls `jarvisService.connect()` or `jarvisService.disconnect()`. Sends `system.toggle` over WebSocket. |
| **Microphone Mute / Unmute** | `dashboard.tsx` (bottom dock) | `isMicMuted` (toggle active / muted) | `toggleMic()`: In `IndexRoot.tsx`, calls `jarvisService.setMute()`. Disables audio tracks on `MediaStream` and sends `audio.control` to backend. |
| **Vision Selector** | `dashboard.tsx` (bottom dock) | Triggers `onVisionClick` | If video is active, calls `stopVision()`. If inactive, opens `showSourceModal`. |
| **Source Uplink Modal** | `jarvis-layout.tsx` (modal overlay) | Camera vs Screen Share | Buttons call `startVision('camera')` (via `getUserMedia` video) or `startVision('screen')` (via `getScreenSourceId` desktop capturer). |
| **Live Clock** | `jarvis-layout.tsx` (top right) | 1 Hz local time display | Memoized `<LiveClock />` component updating internally every 1,000ms. |
| **Window Controls** | `src/components/common/titlebar.tsx` | Minimize, Maximize, Close | Calls `window-min`, `window-max`, `window-close` over IPC, supporting both macOS traffic lights and Windows caption buttons. |
| **Focus Mode Toggle** | `dashboard.tsx` (top of center column) | `isFocusMode` boolean | Expands visualizer to full screen `#020611` background, exits on ESC or button click. |

---

## 5. Technology Stack & Dependencies Audit

| Component | Library / Version in `package.json` | Implementation Location |
| :--- | :--- | :--- |
| **UI Framework** | React `^19.2.8`, React DOM `^19.2.8` | `src/main.tsx`, `src/App.tsx`, `src/IndexRoot.tsx` |
| **Build & Dev Tool** | Vite `^8.0.10`, `@vitejs/plugin-react` `^6.0.1` | `vite.config.ts` |
| **Desktop Runtime** | Electron `40.10.2` | `electron/main.ts`, `electron/preload.ts` |
| **Styling** | Tailwind CSS `^4.2.4`, `@tailwindcss/vite` | `src/assets/main.css` |
| **Motion & Animation** | Motion `^12.38.0` | Layout transitions, modals, tabs |
| **3D & Canvas** | Three.js `^0.180.0`, `@react-three/fiber` `^9.6.1`, `@react-three/drei` `^10.7.7` | `src/components/dashboard/sphere.tsx` |
| **Icons** | `lucide-react` `^0.577.0`, `react-icons` `^5.7.0` | Layouts, widgets, buttons |
| **Terminal** | `@xterm/xterm` `^6.0.0`, `@xterm/addon-fit` `^0.11.0` | `src/components/terminal/terminal.tsx` |
| **State Management** | Zustand `^5.0.14` | `src/store/settings-store.ts`, `workspace-store.ts`, `profile-store.ts` |
| **Virtualization** | `react-virtuoso` `^4.18.11` | `src/pages/task-manager.tsx` |
| **Code Editor** | `@codemirror/*` (v6) | `src/pages/Workspace/CodeWorkspace.tsx` |

---

## 6. Frontend Communication & WebSocket Architecture

The frontend communicates with the backend via two complementary layers:

### Layer 1: Unified WebSocket Contract (`src/lib/gateway-client.ts`)
- **Protocol Definition:** `src/shared/protocol.ts` (defining `WebSocketEnvelope<T>` and message types `user.message`, `audio.control`, `agent.state`, `agent.token`, `agent.complete`, `tool.start`, `tool.result`, `system.metrics`, `client.command`, `error`).
- **Connection Target:** `http://127.0.0.1:8765` (REST) and `ws://127.0.0.1:8765/ws/jarvis` (WebSocket).
- **Features:** Auto-reconnect with exponential backoff, active streaming message map, event listeners for telemetry, state, route, tools, and confirmation dialogs.

### Layer 2: Realtime 60 FPS Visualizer Bridge (`src/services/jarvisBridge.ts`)
- **Connection Target:** `ws://127.0.0.1:8765/ws`.
- **Zero-Re-Render Mutable Store (`jarvisRealtimeRef`):**
  ```typescript
  export const jarvisRealtimeRef = {
    audioLevel: 0,
    voiceState: 'IDLE' as string,
    isSpeaking: false,
    isListening: false,
  };
  ```
  - Receives high-frequency `voice_state` / `agent.state` and audio amplitude envelopes.
  - Updates mutable reference directly without triggering React component re-renders.
  - Consumed directly inside Three.js `useFrame` in `src/components/dashboard/sphere.tsx`.

### Layer 3: Electron Main IPC Supervisor (`electron/preload.ts` & `electron/main.ts`)
- `contextBridge.exposeInMainWorld('jarvis', jarvisApi)` and `'electron'` expose:
  - System hardware metrics (`get-system-stats`, `get-processes`, `kill-process`).
  - Window lifecycle (`window-min`, `window-max`, `window-close`, `window-is-maximized`).
  - Terminal IPC (`terminal-spawn`, `terminal-input`, `terminal-output`, `terminal-resize`).
  - Native file dialogs and screen capture helpers (`getScreenSourceId`).

---

## 7. Conclusions & Implementation Recommendations

1. **UI Immutability Compliance**:
   - The React UI across all 9 navigation tabs (`DASHBOARD`, `WORKSPACE`, `MODULES`, `APPS`, `TASKS`, `NOTES`, `GALLERY`, `TERMINAL`, `SETTINGS`) is well-structured, modular, and visually intact.
   - Per Requirement R1, no visual UI files outside `src/components/widgets/arc-reactor.tsx`, `src/layouts/jarvis-layout.tsx`, and `src/services/theme-manager.ts` should be altered.
2. **Ultron Control Verification**:
   - Ultron controls are already completely absent in `jarvis-layout.tsx` and `theme-manager.ts`. The UI is purely focused on J.A.R.V.I.S.
3. **Arc Reactor / Holographic Visualizer Realization**:
   - The central visualizer currently active is `src/components/dashboard/sphere.tsx`.
   - To strictly fulfill R1.2 and Section 6.6 of the master prompt, `src/components/widgets/arc-reactor.tsx` can either be created with `JARVIS_LIGHTING_CONFIG` and frame-rate-independent delta-time animation physics as specified, or `src/components/dashboard/sphere.tsx` can be retained/aliased to ensure 100% visual stability without breaking existing Three.js scene pipelines.
4. **Backend Gateway Port Parity**:
   - All frontend bridge files (`gateway-client.ts`, `jarvisBridge.ts`, `jarvis-voice-ai.ts`, `scripts/run-jarvis-service.mjs`) consistently point to `127.0.0.1:8765`, ensuring clean plug-and-play alignment with the upcoming FastAPI backend.
