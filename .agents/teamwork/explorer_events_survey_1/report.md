# J.A.R.V.I.S. 11-State Holographic Core Visualizer: Runtime State & Event System Survey

**Investigation Milestone**: Holographic Core Visualizer Event Wiring Survey  
**Investigator**: Teamwork Explorer (`explorer_events_survey_1`)  
**Target Repository**: `e:\Projects\J.A.R.V.I.S Electron App`  
**Reference Visualizer**: `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`  
**Status**: Completed Investigation & Architecture Specification  

---

## Executive Summary

The J.A.R.V.I.S Electron App currently employs a multi-tiered architecture consisting of:
1. **Frontend (Electron Renderer)**: React 19 + Vite + Tailwind CSS + Three.js (`@react-three/fiber` & `@react-three/drei`), utilizing Zustand stores (`useSettingsStore`, `useProfileStore`, `useWorkspaceStore`) and a high-performance zero-re-render mutable reference store (`jarvisRealtimeRef`) for 60 FPS audio visualizer reactivity.
2. **Gateway WebSocket Clients**:
   - `gatewayClient` (`src/lib/gateway-client.ts`) connecting to `ws://127.0.0.1:8765/ws/jarvis` (governed by `src/shared/protocol.ts`).
   - `jarvisBridge` (`src/services/jarvisBridge.ts`) connecting to `ws://127.0.0.1:8765/ws`.
   - `GeminiLiveService` (`src/services/jarvis-voice-ai.ts`) handling live Web Audio API analyser integration and wake-word streams.
   - `HermesAdapter` (`src/services/hermes-adapter.ts`) bridging gateway event streams to window events.
3. **Backend Sidecar (Python FastAPI Gateway on port 8765)**:
   - `backend/main.py`: Full-duplex WebSocket hub managing bidirectional JSON envelopes (`system.metrics`, `agent.state`, `agent.token`, `agent.complete`, `tool.start`, `tool.result`, `audio.control`).
   - `backend/core/hermes_brain.py`: Asynchronous cognitive turn executor dispatching `thinking`, `compressing`, `agent.token`, and `agent.complete`.
   - `backend/voice/audio_pipeline.py`: Conversational full-duplex audio engine with sub-32ms barge-in and 24kHz TTS playback.
   - `backend/core/tool_dispatcher.py`: Parallel tool execution engine running Phase 6 tools across web search, research, coding, vision, and system automation.
   - `backend/security/agent_shield.py` & `ecc_hooks.py`: Real-time threat detection and security policy enforcement.

This survey provides an exact, production-ready blueprint for connecting all application runtime events to the **11 Holographic Core Visualizer States**, complete with state arbitration priority, automatic fallback timeouts, zero-re-render audio syncing, manual testing hotkeys, and clean TypeScript definitions.

---

## 1. Inventory of the 11 Holographic Core Visualizer States

From `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`:

| State ID | Key | Color Name | Hex Code | Visual Geometry & Particle Behavior |
| :--- | :---: | :--- | :---: | :--- |
| **`IDLE`** | `1` | Ice-Cyan | `#67e8f9` | Calm breathing surface wave, slow axial drift, soft dual counter-rotating rings. |
| **`LISTENING`** | `2` | Sky-Cyan | `#00f0ff` | Inward focus contraction, concentric equatorial-to-polar sonar ripples, live mic frequency reactivity. |
| **`THINKING`** | `3` | Amber-Gold | `#fbbf24` | Counter-twisting hemisphere vortex, 3D spherical-harmonic lobes, fast gyroscopic rings. |
| **`SPEAKING`** | `4` | White-Ice | `#e0f2fe` | Multi-band audio reactivity (bass core punch, mid standing waves, treble corona spikes) with speech cadence synthesizer fallback. |
| **`WEB_SEARCH`** | `5` | Cyber Azure | `#38bdf8` | 3D planetary latitude/longitude wireframe globe tilted at 23.5° axial angle with sweeping meridian radar beam and live search hit pings. |
| **`DEEP_RESEARCH`** | `6` | Periwinkle | `#818cf8` | Core splits into 3 nested concentric knowledge shells (dense core, tilted mid-shell, outer halo) counter-rotating in orbital planes. |
| **`CODING`** | `7` | Matrix Mint | `#4ade80` | Morphs from sphere into a beveled 3D holo-cube with cascading vertical digital matrix code streams down all 6 faces. |
| **`VISION_SCAN`** | `8` | Laser Rose | `#f472b6` | Precision horizontal optical lidar ring and laser plane sweeping smoothly from north pole to south pole across surface. |
| **`MEMORY_SYNC`** | `9` | Teal-Cyan | `#2dd4bf` | Opens a central polar tunnel into an Arc-Reactor 3D torus with continuous poloidal particle flow through core. |
| **`EXECUTING_TOOL`** | `0` | Neon Violet | `#c084fc` | High-speed multi-axis spin with crisp octupole geometric facets and accelerated gyroscopic ring rotation. |
| **`ALERT`** | `-` | Crimson-Coral | `#fb7185` | Urgent twin-beat cardiac shockwave (`lub-dub` pulse) with sharp radial warning spikes and rapid pulsing red glow. |

---

## 2. Frontend State Stores, Hooks & Event Systems

### 2.1 State Stores
- **`useSettingsStore` (`src/store/settings-store.ts`)**:
  - Manages persistent settings (`theme`, `voice`, `model`, `computeMode`, `reasoningEffort`, `thinkingEnabled`).
  - Controls active UI color presets via `applyThemeToDom`.
- **`useProfileStore` (`src/store/profile-store.ts`)**:
  - Manages active user profile and system profiles.
- **`jarvisRealtimeRef` (`src/services/jarvisBridge.ts`)**:
  ```ts
  export const jarvisRealtimeRef = {
    audioLevel: 0,
    voiceState: 'IDLE' as string,
    isSpeaking: false,
    isListening: false,
  };
  ```
  - Crucial architectural pattern: **Mutable store bypasses React rendering pipeline completely**, allowing Three.js `useFrame` at 60 FPS to read frequency amplitude and state updates with zero frame drops or React tree re-renders.

### 2.2 Global DOM CustomEvents
Communication between non-React services (WebSockets, IPC) and React components currently relies on `window.dispatchEvent` with typed `CustomEvent` instances:
- `jarvis-state`: Dispatched with state string (e.g., `'IDLE'`, `'SPEAKING'`, `'LISTEN'`). Consumed by `Sphere` in `src/components/dashboard/sphere.tsx` and `MiniOverlay` in `src/components/dashboard/mini-overlay.tsx`.
- `jarvis-voice-state`: Dispatched with `{ state, amplitude, is_speaking }`.
- `jarvis-tool-call`: Dispatched with `{ phase: 'start' | 'result', tool: string, arguments?: any, result?: any, duration_ms?: number }`.
- `jarvis-telemetry`: Dispatched with `{ hardware, network, timestamp }`.
- `jarvis-terminal-log`: Dispatched with `{ level, message, timestamp }`.
- `jarvis-terminal-execute`: Dispatched when code/command execution is sent to terminal.
- `jarvis-agent-response`: Dispatched on LLM final response completion.

### 2.3 Web Audio API Integration
- `GeminiLiveService` (`src/services/jarvis-voice-ai.ts`):
  - Initializes `AudioContext` and `AnalyserNode` (`fftSize = 256`, `smoothingTimeConstant = 0.8`).
  - Directly taps `navigator.mediaDevices.getUserMedia({ audio: true })`.
  - Exposes `jarvisService.analyser`, which `Sphere` reads via `analyser.getByteFrequencyData(dataArray)` into 3 bands:
    - **Bass** (bins 0–15): Powers sphere core punch.
    - **Mid** (bins 16–55): Powers standing surface waves.
    - **Treble** (bins 56–111): Powers corona particle spikes.
  - Includes a procedural **speech cadence synthesizer** that generates organic syllable modulation when TTS audio is playing even if the raw Web Audio analyser is unavailable.

---

## 3. WebSocket Clients & Electron IPC Communication

### 3.1 Gateway WebSocket Client (`src/lib/gateway-client.ts`)
Connects to `ws://127.0.0.1:8765/ws/jarvis` and implements the contract in `src/shared/protocol.ts`:
- **`system.metrics`**: Broadcasts CPU, RAM, GPU, temperatures, and network latency.
- **`agent.state`**: Emits `idle`, `listening`, `transcribing`, `thinking`, `executing_tool`, `speaking`. Dispatches `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: stateVal }))`.
- **`agent.token`**: Delivers live streaming tokens from HermesBrain.
- **`agent.complete`**: Signals completion of assistant response turn.
- **`tool.start`**: Dispatches `jarvis-tool-call` with `{ phase: 'start', tool, arguments }`.
- **`tool.result`**: Dispatches `jarvis-tool-call` with `{ phase: 'result', tool, result, duration_ms }`.
- **`tts_playback`**: Audio payload received from backend 24kHz synthesis; creates HTML5 `Audio`, dispatches `jarvis-state: 'SPEAKING'`, and upon `onended` reverts to `'IDLE'`.
- **`confirmation_request`**: Triggers security confirmation modal for elevated risk tools.
- **`error` / `chat:error`**: Dispatched on failures.

### 3.2 High-Speed Bridge Client (`src/services/jarvisBridge.ts`)
Connects to `ws://127.0.0.1:8765/ws` for legacy and zero-latency telemetry:
- Ingests `voice_state` packets and synchronizes `jarvisRealtimeRef.audioLevel` and `jarvisRealtimeRef.voiceState`.
- Dispatches `jarvis-voice-state` and `jarvis-state`.

### 3.3 Electron IPC Handlers (`electron/`)
Exposed through `window.electron.ipcRenderer` and `window.jarvis` / `window.jarvisDesktop`:
- **Memory Operations**: `save-core-memory` (`electron/handlers/ai/permanent-memory.ts`), `search-core-memory`, `get-history`, `add-message`.
- **Vision & Display**: `window-toggle-fullscreen`, `toggle-overlay`, desktop screen source capture (`desktopCapturer.getSources`).
- **Security**: `check-vault-status`, `verify-vault-pin`, `verify-vault-face`.
- **System**: `get-system-stats`, `open-app`, `take-screenshot`.

---

## 4. Backend Runtime States & Event Emission

### 4.1 HermesBrain (`backend/core/hermes_brain.py`)
Autonomous multi-turn reasoning engine. Emits:
1. `agent.state` -> `thinking`: Emitted immediately when `run_turn` begins.
2. `agent.state` -> `compressing`: Emitted if conversation history exceeds context limit and requires vector summarization.
3. `agent.token`: Emitted on every generated token chunk.
4. `agent.complete`: Emitted when generation finishes, with full text, token counts, and elapsed latency.
5. `interrupted`: Emitted on conversational barge-in or user abort (<15ms latency).
6. `agent.state` -> `idle`: Emitted after turn concludes.

### 4.2 Conversational Audio Pipeline (`backend/voice/audio_pipeline.py`)
1. Wake Word Detection (`wakeword_engine.py`): Emits `wake_word_detected`.
2. Voice State Broadcasting:
   - `on_speaking()`: Transitions state to `speaking`.
   - `trigger_barge_in()`: Instantly halts sounddevice playback, interrupts `HermesBrain`, and broadcasts `agent.state: 'listening'` and `jarvis-voice-state: { state: 'listening', interrupted: True }`.
   - 24kHz OmniVoice TTS playback: Emits `agent.complete` containing synthesized audio base64.

### 4.3 Tool Dispatcher (`backend/core/tool_dispatcher.py`)
Registered Phase 6 tools and their operational classification:
- **Web Extraction & Browser Tools**:
  - `crawl4ai_extract`: Web scraping and BM25 content filtering.
  - `browser_use_background`: Headless Chrome CDP automation.
- **Multi-Source Research Tools**:
  - `gpt_researcher_report`: Academic and web research synthesis.
  - `delegate_task`: Spawns planner/architect subagents for architectural decomposition.
- **Code & Document Transformation**:
  - `markitdown_convert`: Multi-format parsing (PDF, DOCX, XLSX, code files).
  - Terminal code executions.
- **Vision & Visual Grounding**:
  - `agent_s3_visual_task`: Desktop GUI grounding via OmniParser V2.
  - `windows_mcp_snapshot`: Windows UI Automation control hierarchy capture.
  - Camera/Vision hub frame capture (`backend/senses/camera_hub.py`).
- **Memory & Search**:
  - `memory`: Long-term fact persistence.
  - `session_search`: FTS5 full-text conversation search.
  - `/v1/core-memory`: Hybrid RAG and Instinct engine persistence.
- **System & Automation**:
  - `windows_mcp_click`, `windows_mcp_type`, `windows_mcp_shortcut`.
  - `mobilerun_phone_task`: Wireless Android ADB control.
  - `todo`: Action item management.
- **Security & Safety Guardrails**:
  - `AgentShield` block (`pre_tool_hook` failure): `PermissionError`.
  - `ToolLoopHaltException`: Repetitive execution streak detection.

---

## 5. Comprehensive Mapping: Application Events to the 11 Holographic States

To bridge all application operations into the visualizer, we map runtime events to the 11 core states using a priority-driven classification matrix:

```
+---------------------------------------------------------------------------------------+
|                                11-STATE ARBITRATION PIPELINE                          |
+---------------------------------------------------------------------------------------+
|  [Security Alert / Hardware Alarm / Tool Loop Halt / Critical Error]                 |
|       ==> ALERT (Priority 100)                                                        |
|                                                                                       |
|  [Camera / Screen Share Active / Vision AI Processing / agent_s3 / windows_mcp_snap]  |
|       ==> VISION_SCAN (Priority 90)                                                   |
|                                                                                       |
|  [TTS Playback / Audio Out / agent.token / message.delta / isSpeaking: true]          |
|       ==> SPEAKING (Priority 80)                                                      |
|                                                                                       |
|  [Active Tool Invocations] (Priority 70):                                             |
|       - crawl4ai_extract, browser_use, /search           ==> WEB_SEARCH               |
|       - gpt_researcher_report, delegate_task, subagent   ==> DEEP_RESEARCH            |
|       - markitdown_convert, code execution, terminal run ==> CODING                   |
|       - memory, session_search, core_memory             ==> MEMORY_SYNC               |
|       - windows_mcp_click/type/shortcut, mobilerun, todo ==> EXECUTING_TOOL          |
|                                                                                       |
|  [hermes_brain: thinking / compressing / prompt building / gateway processing]        |
|       ==> THINKING (Priority 60)                                                      |
|                                                                                       |
|  [Wake Word Detected / Mic Active & User Speaking / Barge-In Triggered]               |
|       ==> LISTENING (Priority 50)                                                     |
|                                                                                       |
|  [No Active Action / System Standby / Turn Complete / Inactive]                        |
|       ==> IDLE (Priority 10 - Default Fallback)                                       |
+---------------------------------------------------------------------------------------+
```

### Detailed Event-to-State Mapping Table

| Visualizer State | Triggering Application Events & IPC Messages | Subsystem Source | Deactivation / Fallback Condition |
| :--- | :--- | :--- | :--- |
| **`IDLE`** | `agent.complete`, `cancel_speech`, `audio.onended`, startup, conversation turn finished. | `HermesBrain`, `AudioPipeline`, `gatewayClient` | Any active higher-priority event. |
| **`LISTENING`** | `wake_word_detected`, `agent.state: 'listening'`, `jarvis-voice-state: { state: 'listening' }`, user speech input, mic active with signal. | `AudioPipeline`, `wakeword_engine`, `GeminiLiveService` | User stops speaking; transitions to `THINKING` upon message submission. |
| **`THINKING`** | `agent.state: 'thinking'`, `agent.state: 'compressing'`, `chat:send`, `user.message`, `processing`, model routing. | `HermesBrain`, `ContextCompressor`, `ModelRouter` | First token chunk arrives (`agent.token` -> `SPEAKING`) or tool starts (`tool.start`). |
| **`SPEAKING`** | `tts_playback`, `agent.token`, `chat:delta`, `message.delta`, `AudioPipeline.on_speaking()`, `jarvisRealtimeRef.isSpeaking = true`. | `AudioPipeline`, `OmniVoiceService`, `gatewayClient` | Audio playback ends (`audio.onended`), speech cancelled (`cancel_speech`), or barge-in. |
| **`WEB_SEARCH`** | `tool.start` with `tool: 'crawl4ai_extract'` or `'browser_use_background'`, or HTTP `/search` query. | `ToolDispatcher`, `Crawl4AIService`, `BrowserUseRunner` | `tool.result` received for search tool; reverts to `THINKING` or `SPEAKING`. |
| **`DEEP_RESEARCH`**| `tool.start` with `tool: 'gpt_researcher_report'` or `'delegate_task'`, or multi-agent planning turns. | `ToolDispatcher`, `GPTResearcherService`, `HermesBrain` | `tool.result` received for research tool. |
| **`CODING`** | `tool.start` with `tool: 'markitdown_convert'`, terminal script execution (`jarvis-terminal-execute`), workspace file code modifications. | `ToolDispatcher`, `MarkItDownService`, `Terminal` | Code operation or script execution completes. |
| **`VISION_SCAN`** | `startVision('camera' | 'screen')`, `isVideoOn: true`, `tool.start` with `agent_s3_visual_task` or `windows_mcp_snapshot`. | `IndexRoot`, `CameraHub`, `AgentS3Runner`, `WindowsMCPBridge` | Vision stopped (`stopVision()`), or tool completed. |
| **`MEMORY_SYNC`** | `saveCoreMemory`, `retrieveCoreMemory`, `tool.start` with `memory` or `session_search`, `/v1/core-memory` updates. | `HybridMemory`, `SessionDB`, `InstinctEngine`, IPC | Memory read/write completes. |
| **`EXECUTING_TOOL`**| `tool.start` with `windows_mcp_*`, `mobilerun_phone_task`, `todo`, or any generic unmapped tool. | `ToolDispatcher`, `ECCHookDispatcher` | `tool.result` received for tool. |
| **`ALERT`** | `AgentShield` security policy block (`PermissionError`), `confirmation_request` (CRITICAL/HIGH), `ToolLoopHaltException`, `error` / `chat:error`, critical battery (<10%), thermal throttle (>85°C). | `AgentShield`, `PowerGuardian`, `ECCHookDispatcher` | User dismisses alert, confirmation resolved, or 5-second automatic timeout. |

---

## 6. Visualizer Consumption Architecture & State Transition Pipeline

### 6.1 State Transition Engine (`VisualizerStateCoordinator`)
To prevent state flapping (e.g., rapid alternation between `THINKING` and `SPEAKING` during token streaming), the visualizer should consume events through a state coordinator adhering to these rules:

1. **Exponential Decay Blending**:
   In Three.js `useFrame`, morph target weights blend smoothly via:
   ```ts
   const dt = Math.max(0, Math.min(0.05, delta));
   const damp = 1 - Math.exp(-6.2 * dt);
   for (const key of STATE_KEYS) {
     weights.current[key] += ((activeState === key ? 1 : 0) - weights.current[key]) * damp;
   }
   ```
2. **Minimum State Dwell Time**:
   Transient states like `WEB_SEARCH`, `MEMORY_SYNC`, and `EXECUTING_TOOL` should maintain a minimum dwell time of **350ms** so the visual morph is perceived smoothly by the user even if a fast tool finishes in 50ms.
3. **Safety Fallback to IDLE**:
   - When in `THINKING`, if no tokens or tool events arrive within **12 seconds**, auto-revert to `IDLE`.
   - When in `SPEAKING`, if no audio or token activity occurs for **1.5 seconds**, auto-revert to `IDLE`.
   - When in `ALERT`, automatically clear non-fatal alerts after **5.0 seconds** unless persistent.

### 6.2 Manual State Override & Testing Capabilities
For developer testing, HUD telemetry demonstration, and presentation modes:
1. **Keyboard Hotkeys**:
   Keys `1` through `0` and `-` directly trigger states:
   - `1`: `IDLE`
   - `2`: `LISTENING`
   - `3`: `THINKING`
   - `4`: `SPEAKING`
   - `5`: `WEB_SEARCH`
   - `6`: `DEEP_RESEARCH`
   - `7`: `CODING`
   - `8`: `VISION_SCAN`
   - `9`: `MEMORY_SYNC`
   - `0`: `EXECUTING_TOOL`
   - `-`: `ALERT`
   *(Hotkeys are automatically ignored when focus is inside text inputs or textareas)*.
2. **HUD Debug State Dock / Selector**:
   A compact dropdown or bottom dock allows forcing and locking any state indefinitely for shader inspection.
3. **Auto-Tour Mode**:
   Cycles through all 11 states sequentially (3.5 seconds each) with full morphological transition.

---

## 7. Recommended TypeScript Interfaces & Event Listener Architecture

Create a dedicated state coordination module in `src/services/visualizer-state-manager.ts` and declare strict interfaces:

```typescript
// =============================================================================
// src/types/visualizer.ts
// =============================================================================

export type JarvisVisualState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'WEB_SEARCH'
  | 'DEEP_RESEARCH'
  | 'CODING'
  | 'VISION_SCAN'
  | 'MEMORY_SYNC'
  | 'EXECUTING_TOOL'
  | 'ALERT';

export interface VisualStateConfig {
  key: string;
  id: JarvisVisualState;
  colorName: string;
  hex: string;
  priority: number;
  description: string;
}

export interface StateTransitionEvent {
  state: JarvisVisualState;
  source: 'gateway' | 'voice' | 'tool' | 'vision' | 'security' | 'manual';
  details?: string;
  timestamp: number;
  lockDurationMs?: number;
}

export interface ToolStateMappingRule {
  toolPattern: RegExp | string;
  targetState: JarvisVisualState;
}
```

```typescript
// =============================================================================
// src/services/visualizer-state-manager.ts
// =============================================================================

import { jarvisRealtimeRef } from '@/services/jarvisBridge';

export const STATE_PRIORITIES: Record<JarvisVisualState, number> = {
  ALERT: 100,
  VISION_SCAN: 90,
  SPEAKING: 80,
  WEB_SEARCH: 70,
  DEEP_RESEARCH: 70,
  CODING: 70,
  MEMORY_SYNC: 70,
  EXECUTING_TOOL: 70,
  THINKING: 60,
  LISTENING: 50,
  IDLE: 10,
};

const TOOL_MAPPINGS: Record<string, JarvisVisualState> = {
  crawl4ai_extract: 'WEB_SEARCH',
  browser_use_background: 'WEB_SEARCH',
  gpt_researcher_report: 'DEEP_RESEARCH',
  delegate_task: 'DEEP_RESEARCH',
  markitdown_convert: 'CODING',
  agent_s3_visual_task: 'VISION_SCAN',
  windows_mcp_snapshot: 'VISION_SCAN',
  memory: 'MEMORY_SYNC',
  session_search: 'MEMORY_SYNC',
};

class VisualizerStateManager {
  private currentState: JarvisVisualState = 'IDLE';
  private manualOverride: JarvisVisualState | null = null;
  private overrideTimeout: any = null;
  private fallbackTimer: any = null;

  public getState(): JarvisVisualState {
    if (this.manualOverride) return this.manualOverride;
    return this.currentState;
  }

  public setState(nextState: JarvisVisualState, forceDurationMs?: number): void {
    if (forceDurationMs) {
      this.manualOverride = nextState;
      clearTimeout(this.overrideTimeout);
      this.overrideTimeout = setTimeout(() => {
        this.manualOverride = null;
        this.emitState();
      }, forceDurationMs);
    } else {
      this.currentState = nextState;
    }
    this.emitState();
  }

  public handleToolStart(toolName: string): void {
    const mappedState = TOOL_MAPPINGS[toolName] || 'EXECUTING_TOOL';
    this.setState(mappedState);
  }

  public handleToolResult(): void {
    // Return to THINKING if brain is still processing, else IDLE
    this.setState('THINKING');
    this.resetFallbackTimer(8000);
  }

  public resetFallbackTimer(timeoutMs: number = 5000): void {
    clearTimeout(this.fallbackTimer);
    this.fallbackTimer = setTimeout(() => {
      if (this.currentState !== 'IDLE' && !this.manualOverride) {
        this.setState('IDLE');
      }
    }, timeoutMs);
  }

  private emitState(): void {
    const active = this.getState();
    jarvisRealtimeRef.voiceState = active;
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: active }));
  }
}

export const visualizerManager = new VisualizerStateManager();
```

---

## 8. Integration Plan & File Verification Checklist

When implementing the visualizer replacement in subsequent tasks:

1. **`src/components/dashboard/sphere.tsx`**:
   - Replace sphere geometry and shaders with the 11-state morphing particle system from `c:\Users\utpal\Downloads\j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.
   - Update `STATE_COLORS` to match the exact 11 color palette (e.g. `#67e8f9` for IDLE, `#00f0ff` for LISTENING, etc.).
   - Connect `useFrame` directly to `jarvisRealtimeRef.voiceState` and `jarvisRealtimeRef.audioLevel`.
   - Preserve keyboard event listener for keys `1` through `0` and `-`.

2. **`src/pages/dashboard.tsx`**:
   - Ensure `<Sphere />` mounts cleanly in both main dashboard view and fullscreen focus mode.
   - Maintain the `isSystemActive` scale and opacity transitions.

3. **`src/lib/gateway-client.ts`**:
   - Verify `agent.state`, `tool.start`, `tool.result`, `tts_playback`, and `error` dispatch to `visualizerManager` or `window.dispatchEvent('jarvis-state')`.
   - Map tool names (`crawl4ai_extract`, `gpt_researcher_report`, `markitdown_convert`, etc.) to their corresponding visualizer states.

4. **Testing & Diagnostics**:
   - Verify test suite passes (`npm run typecheck`, `npm run check:lint`, `npm run test:ui`).
   - Launch application in development mode (`npm run dev`) to confirm 60 FPS WebGL rendering with zero console errors or shader warnings.
