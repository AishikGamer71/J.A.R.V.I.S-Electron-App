# Milestone 2 Technical Investigation Report: Visualizer State & Event Wiring

**Document Version**: 2.0.0  
**Investigator**: Teamwork Explorer 2 (`explorer_m2_2`)  
**Workspace**: `e:\Projects\J.A.R.V.I.S Electron App`  
**Milestone**: Milestone 2 (Visualizer State & Event Wiring)  
**Parent Orchestrator**: `6b8fe7dc-259c-49f7-b0b6-2f959f447b00`  
**Date**: November 11, 2026  

---

## 1. Executive Summary

Milestone 1 successfully delivered the self-contained 3D Holographic Core Visualizer subsystem under `src/components/dashboard/holographic-core/` and drop-in wrapper `src/components/dashboard/sphere.tsx`, establishing all 4 optical layers, 11 cognitive states, continuous exponential weight morphing, and Web Audio reactivity.

The objective of **Milestone 2** is to seamlessly wire this 11-state visualizer to application runtime events, agent state transitions, tool execution flows, speech synthesis, vision streams, keyboard hotkeys, and live audio levels.

This investigation provides:
1. **Component Mounting & State Ingestion Audit**: An analysis of how `<Sphere />` is mounted in `src/pages/dashboard.tsx` (Focus Mode line 606 and Main View line 695) and why neither call site currently passes props, necessitating a robust event-driven and hook-backed state bridge.
2. **State Arbitration & Lifecycle Management Architecture**: A formal 7-level priority hierarchy:
   $$\text{ALERT} > \text{VISION\_SCAN} > \text{SPEAKING} > \text{ACTIVE\_TOOL} > \text{THINKING} > \text{LISTENING} > \text{IDLE}$$
   with deterministic tool classification, automatic fallback timeouts (15s–30s hang guard), and post-completion dwell times (2000ms tool dwell, 4000ms alert dwell, 350ms speech decay).
3. **`jarvis-state` CustomEvent Unpacking**: Full polymorphic payload resolution supporting `{ detail: { state: HolographicState } }`, `{ detail: HolographicState }`, string primitives, legacy aliases (`LISTEN`, `PROCESSING`), and nested objects via `unpackJarvisStateDetail`.
4. **Keyboard Hotkey Controller & Strict Guards**: Hotkey mapping for keys `1` through `0` and `-` with multi-layer input guards (`<input>`, `<textarea>`, `<select>`, `isContentEditable`, `closest('[contenteditable]')`) and modifier key protection (`e.ctrlKey`, `e.altKey`, `e.metaKey`) to prevent hotkey collisions with OS or browser actions.
5. **Live Audio Streaming & Pulse Reactivity**: A dual-feed pipeline piping live microphone RMS levels and TTS playback audio into mutable `jarvisRealtimeRef.audioLevel`, enabling high-energy 60 FPS pulsing without Virtual DOM re-render thrashing.
6. **Production-Ready File Architecture & Code Blueprints**: Modular designs for `state-arbitrator.ts`, `use-visualizer-state.ts`, and `keyboard-controller.ts`, complete with empirical test specifications.

---

## 2. Component Mounting & State Flow in Dashboard

### 2.1 Mount Points in `src/pages/dashboard.tsx`

Inspection of `src/pages/dashboard.tsx` reveals two mount locations for the visualizer:

1. **Focus Mode (Expanded HUD)** — Lines 605–607:
   ```tsx
   <div className="w-[84vmin] h-[84vmin] max-w-[95vw] max-h-[95vh] flex items-center justify-center pointer-events-none">
     <Sphere />
   </div>
   ```
2. **Main Dashboard View (Center Canvas)** — Lines 692–696:
   ```tsx
   {/* 3D Sphere - Zero-re-render memoized wrapper */}
   <div
     className={`w-[60vh] h-[60vh] max-w-full transition-all duration-1000 ${
       isSystemActive ? 'opacity-100 scale-100' : 'opacity-85 scale-90 grayscale'
     } pointer-events-none`}
   >
     <Sphere />
   </div>
   ```

### 2.2 Critical Mounting Observations

1. **Zero Props Passed at Call Sites**: Both `<Sphere />` instances are instantiated without props (`<Sphere />`). Neither `activeTool`, `state`, `isSpeaking`, `isListening`, nor `error` is provided by `dashboard.tsx`.
2. **Existing Disconnected Local State in `dashboard.tsx`**:
   - `activeTool` state exists at line 375:
     ```tsx
     const [activeTool, setActiveTool] = useState<{ tool: string; phase: 'start' | 'result' } | null>(null)
     ```
     and is populated via `window.addEventListener('jarvis-tool-call', handleTool)` at lines 378–389. However, this state is only rendered in the chat panel badge (lines 739–747) and is **never passed to `<Sphere />`**.
   - `isVideoOn` and `visionMode` (`'camera' | 'screen' | 'none'`) are received from props (lines 46–47, 309–310) and run face detection (lines 470–520), but are **never passed to `<Sphere />`**.
3. **Current State Resolution Inside `HolographicCoreInner`**:
   Because `props` are empty, `resolveActiveState(props, realtimeVoice)` in `holographic-core-scene.tsx` (lines 179–180) evaluates:
   - Level 1 (`props.overrideState` / `props.state`): `undefined`
   - Level 2 (`props.error`): `undefined`
   - Level 3 (`props.activeTool`): `undefined`
   - Level 4 (`props.isSpeaking` / `isThinking` / `isListening`): `undefined`
   - Level 5 (`realtimeVoice`): Evaluates `realtimeBusState.current || jarvisRealtimeRef.voiceState`.
   - Level 6: Falls back to `'IDLE'`.

**Architectural Implication**:  
The visualizer currently depends entirely on `realtimeBusState.current` (populated by `window.addEventListener('jarvis-state')`) and `jarvisRealtimeRef.voiceState`. Therefore:
- The event wiring and state arbitration engine must either dispatch canonical `jarvis-state` events OR expose a zero-re-render hook/props adapter so that both `<Sphere />` instances automatically transition across all 11 states without requiring invasive rewrites of `dashboard.tsx`.

---

## 3. State Arbitration & Priority Engine Design

### 3.1 Priority Hierarchy Specification

In complex conversational agent interactions, multiple events occur concurrently (e.g., an LLM emits reasoning tokens while a background web crawl executes, or TTS begins speaking while a vision stream is running). A strict priority arbitration hierarchy is required to eliminate visual flicker and state thrashing.

The canonical priority order is:

$$\mathbf{ALERT} > \mathbf{VISION\_SCAN} > \mathbf{SPEAKING} > \mathbf{ACTIVE\_TOOL} > \mathbf{THINKING} > \mathbf{LISTENING} > \mathbf{IDLE}$$

```
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 7: ALERT (#fb7185)                                              │
│ Trigger: Security blocks, fatal errors, AgentShield alarms, '-' hotkey │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 6: VISION_SCAN (#f472b6)                                         │
│ Trigger: isVideoOn (camera/screen), face detection, visual grounding   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 5: SPEAKING (#e0f2fe)                                            │
│ Trigger: TTS audio playback, voice pipeline output, '4' hotkey        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4: ACTIVE_TOOL                                                   │
│   ├── WEB_SEARCH     (#38bdf8): crawl4ai, browser_use, web scraping    │
│   ├── DEEP_RESEARCH  (#818cf8): gpt_researcher, delegate_task          │
│   ├── CODING         (#4ade80): markitdown, terminal, code exec       │
│   ├── MEMORY_SYNC    (#2dd4bf): session_search, memory persistence     │
│   └── EXECUTING_TOOL (#c084fc): windows_mcp_*, mobilerun, other MCP    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 3: THINKING (#fbbf24)                                            │
│ Trigger: agent.state = 'thinking', token generation, '3' hotkey        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 2: LISTENING (#00f0ff)                                           │
│ Trigger: mic unmuted, agent.state = 'listening', wake word, '2' hotkey │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: IDLE (#67e8f9)                                                │
│ Trigger: Baseline quiescent state, system inactive, '1' hotkey         │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Priority Differences from Milestone 1

In Milestone 1's preliminary implementation (`src/components/dashboard/holographic-core/state-machine.ts` lines 89–104):
- `props.activeTool` was evaluated at Level 3, **before** `props.isSpeaking` (Level 4).
- In Milestone 2:
  1. **`SPEAKING` must take precedence over `ACTIVE_TOOL`**: When J.A.R.V.I.S. speaks to the user while background tool cleanup or multi-step execution occurs, the visualizer must pulse to the assistant's voice rather than staying stuck in a tool state.
  2. **`VISION_SCAN` is elevated above `SPEAKING` and `ACTIVE_TOOL`**: When optical vision analysis or camera tracking is active, the lidar slice ring and scanning plane must be visually prominent. Only critical system `ALERT` conditions can preempt vision.
  3. **Realtime event bus states must participate in hierarchical comparison** rather than being a low-priority catch-all beneath booleans.

### 3.3 Comprehensive Tool-to-State Mapping Catalog

Based on the survey of `backend/core/tool_dispatcher.py`, `src/lib/gateway-client.ts`, and Phase 6 capabilities:

| Registered Tool / Action | Target Holographic State | Hex Code | Visual Morphology |
| :--- | :--- | :--- | :--- |
| `crawl4ai_extract`<br>`browser_use_background`<br>`google_web_search`<br>`web_scrape` | **`WEB_SEARCH`** | `#38bdf8` | 23.5° tilted 3D latitude/longitude globe with rotating radar meridian sweep |
| `gpt_researcher_report`<br>`delegate_task`<br>`data_analyzer`<br>`deep_investigate` | **`DEEP_RESEARCH`** | `#818cf8` | 3 nested concentric shells (0.52 core, 0.88 mid-shell, 1.20 outer halo) counter-rotating |
| `markitdown_convert`<br>`terminal_bash_exec`<br>`shell_command`<br>`file_editor`<br>`code_interpreter` | **`CODING`** | `#4ade80` | Morphs into beveled holo-cube with cascading digital matrix rain |
| `agent_s3_visual_task`<br>`camera_stream_read`<br>`mediapipe_face_mesh`<br>`lidar_depth_scan` | **`VISION_SCAN`** | `#f472b6` | Sweeping horizontal optical lidar slice ring ($y = \sin(2.1t) \cdot 0.94$) |
| `memory`<br>`session_search`<br>`vector_store_recall`<br>`sqlite_db_query`<br>`state_db_*` | **`MEMORY_SYNC`** | `#2dd4bf` | Polar tunnel opens into Arc-Reactor 3D torus with continuous poloidal flow |
| `windows_mcp_snapshot`<br>`windows_mcp_click`<br>`windows_mcp_type`<br>`windows_mcp_shortcut`<br>`mobilerun_phone_task`<br>`todo`, `add`, `square` | **`EXECUTING_TOOL`** | `#c084fc` | High-speed multi-axis spin with crisp octupole facets and accelerated gyroscopes |

*Note on Regex Ordering*: In `classifyToolNameToState`, the pattern for `DEEP_RESEARCH` (`/research|delegate|investigate|analyze/i`) must be matched **before** `WEB_SEARCH` (`/search|crawl|browse|web/i`) to ensure tools such as `gpt_researcher_query` are correctly classified as `DEEP_RESEARCH` rather than swallowed by `search`.

### 3.4 Lifecycle Management, Dwell Times & Fallback Timeouts

To prevent abrupt visual cuts and guard against hung processes, the state arbitrator must enforce deterministic lifecycle timing:

1. **Tool Execution Dwell Time (`TOOL_DWELL_MS = 2000ms`)**:
   - When a tool begins (`tool.start`), the visualizer immediately transitions to the mapped tool state (e.g. `WEB_SEARCH`).
   - When the tool finishes (`tool.result`), the visualizer remains in that state for a **2000ms dwell window**. This allows the user to perceive the completed morph (e.g. globe rotation, shell splitting) before returning to `THINKING` (if LLM generation continues) or `IDLE`.
2. **Tool Fallback Timeout (`TOOL_TIMEOUT_MS = 20000ms`)**:
   - If an asynchronous tool hangs or the backend disconnects before emitting `tool.result`, the tool state is forcefully expired after **20 seconds**, reverting to the underlying agent state (`THINKING` or `IDLE`).
3. **Alert Dwell Time (`ALERT_DWELL_MS = 4000ms`)**:
   - Non-fatal transient alerts (e.g. keypress `-` or temporary warning notifications) remain active for **4000ms** (approximately 4.7 cardiac shockwave cycles at 1.18 Hz), then automatically decay back to the previous state.
   - Persistent errors (such as `props.error` being set) remain in `ALERT` indefinitely until cleared.
4. **Speech Decay Tail (`SPEECH_TAIL_MS = 350ms`)**:
   - When TTS audio stops or `audio.onended` fires, a 350ms decay tail prevents sudden visual popping before transitioning to `LISTENING` (in conversational mode) or `IDLE`.

---

## 4. `jarvis-state` CustomEvent Ingestion & Payload Specification

### 4.1 Supported Payload Schemas

External services, Electron IPC handlers, and developer tools dispatch `jarvis-state` events in multiple formats. The visualizer's event listener must accept all of the following:

```typescript
// 1. PROJECT.md standard object payload:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: { state: 'WEB_SEARCH' }
}));

// 2. String primitive payload:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: 'SPEAKING'
}));

// 3. Lowercase & whitespace padded:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: { state: '  deep_research  ' }
}));

// 4. Voice state envelope:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: { voiceState: 'LISTENING', amplitude: 0.85 }
}));

// 5. Nested event payload:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: { detail: { state: 'ALERT' } }
}));

// 6. Legacy backend aliases:
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: 'PROCESSING' // -> Maps to THINKING
}));
window.dispatchEvent(new CustomEvent('jarvis-state', {
  detail: 'LISTEN'     // -> Maps to LISTENING
}));
```

### 4.2 Robust Unpacker Implementation

`unpackJarvisStateDetail` in `src/components/dashboard/holographic-core/state-machine.ts` already contains normalization logic. However, in `holographic-core-scene.tsx` (lines 94–103), the event handler currently uses manual extraction:

```typescript
// Current manual unpacking in holographic-core-scene.tsx:
const handleJarvisState = (e: Event) => {
  const customDetail = (e as CustomEvent).detail
  if (customDetail) {
    if (typeof customDetail === 'object' && customDetail !== null && 'state' in customDetail) {
      realtimeBusState.current = String((customDetail as { state: unknown }).state)
    } else {
      realtimeBusState.current = String(customDetail)
    }
  }
}
```

**Recommended Enhancement**: Replace this with direct invocation of `unpackJarvisStateDetail`:
```typescript
const handleJarvisState = (e: Event) => {
  const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
  if (unpacked) {
    realtimeBusState.current = unpacked
  }
}
```
This guarantees that aliases, lowercase strings, voice state envelopes, and nested payloads are instantly normalized to one of the 11 canonical states.

---

## 5. Keyboard Hotkey Controller & Event Guards

### 5.1 Canonical Hotkey Mapping

For rapid interactive testing and HUD control, numeric keys map to the 11 states:

| Key | State ID | Hex Color | Description |
| :---: | :--- | :--- | :--- |
| `1` | `IDLE` | `#67e8f9` | Calm breathing surface wave |
| `2` | `LISTENING` | `#00f0ff` | Attentive contraction + sonar ripples |
| `3` | `THINKING` | `#fbbf24` | Hemisphere vortex twist + fast gyros |
| `4` | `SPEAKING` | `#e0f2fe` | Audio reactive core punch + corona |
| `5` | `WEB_SEARCH` | `#38bdf8` | Tilted 3D globe + radar sweep |
| `6` | `DEEP_RESEARCH` | `#818cf8` | 3 concentric nested shells |
| `7` | `CODING` | `#4ade80` | Beveled holo-cube + matrix code stream |
| `8` | `VISION_SCAN` | `#f472b6` | Optical lidar slice ring sweep |
| `9` | `MEMORY_SYNC` | `#2dd4bf` | Arc-Reactor torus + poloidal flow |
| `0` | `EXECUTING_TOOL` | `#c084fc` | Multi-axis spin + octupole facets |
| `-` | `ALERT` | `#fb7185` | Twin-beat cardiac shockwave (lub-dub) |

### 5.2 Mandatory Hotkey Guards

Inspection of `holographic-core-scene.tsx` lines 105–119 revealed two significant vulnerabilities:
1. **Modifier Key Collisions**: Pressing `Ctrl+-` (zoom out), `Ctrl+1` (browser tab 1), `Alt+1` (window switch), or `Cmd+1` (macOS) currently triggers visualizer state transitions.
2. **Rich Text & ContentEditable Leakage**: Typing in rich-text divs, chat markdown editors, or Monaco/code inputs leaks hotkeys into the visualizer.

The comprehensive guard predicate must enforce:

```typescript
export function shouldIgnoreKeyboardShortcut(e: KeyboardEvent): boolean {
  // 1. Guard against modifier keys (Ctrl, Alt, Meta/Command)
  if (e.ctrlKey || e.altKey || e.metaKey) {
    return true
  }

  // 2. Guard against standard form input elements
  const target = e.target as HTMLElement | null
  if (!target) return false

  const tagName = target.tagName?.toUpperCase()
  if (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT') {
    return true
  }

  // 3. Guard against contenteditable elements
  if (target.isContentEditable) {
    return true
  }
  if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable]')) {
    return true
  }

  // 4. Guard against code editors and terminal surfaces
  if (target.closest && target.closest('.monaco-editor, .xterm, [role="textbox"]')) {
    return true
  }

  return false
}
```

When a valid shortcut is triggered:
1. The state is updated in the visualizer engine.
2. A CustomEvent `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))` is dispatched so that surrounding UI elements (e.g. `mini-overlay.tsx`) synchronize immediately.

---

## 6. Live Audio Streaming & Dynamic Reactivity

### 6.1 Audio Pipeline Anatomy

In `src/components/dashboard/holographic-core/audio-bridge.ts`, the visualizer computes 3 frequency bands:
- **Bass** (Bins 0–15, $0\text{ Hz}$ to $\sim 2.8\text{ kHz}$): Expands volumetric core glow scale and drives Ring 1 radial dilation.
- **Mid** (Bins 16–55, $\sim 2.8\text{ kHz}$ to $\sim 9.8\text{ kHz}$): Modulates surface standing waves and Ring 2 scale.
- **Treble** (Bins 56–111, $\sim 9.8\text{ kHz}$ to $\sim 19.6\text{ kHz}$): Drives outer particle corona spikes.

```
                  ┌───────────────────────────────────────────────┐
                  │            LIVE MICROPHONE INPUT              │
                  │   navigator.mediaDevices.getUserMedia(...)     │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
┌────────────────────────┐      ┌───────────────────┐      ┌───────────────────────────┐
│     TTS AUDIO DATA     │      │   Web Audio API   │      │    GATEWAY WEBSOCKET      │
│  playTtsAudio(base64)  │─────▶│   AnalyserNode    │◀─────│ voice_state.amplitude    │
└───────────┬────────────┘      │   (fftSize: 256)  │      └─────────────┬─────────────┘
            │                   └─────────┬─────────┘                    │
            │                             │                              │
            ▼                             ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              ZERO-RE-RENDER MUTABLE BRIDGE                           │
│                      jarvisRealtimeRef.audioLevel = currentAmplitude                  │
└─────────────────────────────────────────┬────────────────────────────────────────────┘
                                          │ Direct 60 FPS sampling in useFrame
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                             3-BAND AUDIO REACTIVITY BRIDGE                           │
│       AudioReactivityBridge.update(dt, t, activeState, props.audioLevel)             │
│        - Bass: Bins 0-15  ==> Core scale + Ring 1 expansion                          │
│        - Mid:  Bins 16-55 ==> Surface waves + Ring 2 scale                           │
│        - Treb: Bins 56-111==> Corona spikes                                          │
│        - Fallback: Harmonic speech cadence simulation (< 0.03 threshold)             │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Current Audio Pipeline Limitations

1. **Microphone Channel**: `jarvisService.analyser` is connected to the microphone input in `src/services/jarvis-voice-ai.ts` (lines 38–41). When the user speaks, `AudioReactivityBridge` directly samples this analyser at 60 FPS.
2. **TTS Playback Disconnect**: In `src/lib/gateway-client.ts` (lines 378–404), `playTtsAudio` creates an HTML5 `new Audio(...)` element. This element plays directly to speakers without connecting to the `AudioContext`. As a result:
   - `jarvisService.analyser` registers **zero amplitude** during assistant speech.
   - `jarvisRealtimeRef.audioLevel` remains **0**.
   - The visualizer falls back to the autonomous harmonic speech cadence simulation (`audio-bridge.ts` lines 75–84). While aesthetically functional, it does not track real speech cadence or volume.

### 6.3 Unified Audio Level Piping Architecture

To achieve true live reactivity during both user speech and assistant TTS:

1. **Routing TTS Audio through Web Audio `AnalyserNode`**:
   In `gateway-client.ts`, when `playTtsAudio` is called:
   ```typescript
   // Connect HTMLAudioElement to shared AudioContext analyser
   if (jarvisService?.audioContext && jarvisService?.analyser) {
     const ctx = jarvisService.audioContext
     if (ctx.state === 'suspended') ctx.resume()
     const source = ctx.createMediaElementSource(audio)
     source.connect(jarvisService.analyser)
     jarvisService.analyser.connect(ctx.destination)
   }
   ```
2. **Mutable Amplitude Metering Loop for TTS**:
   Concurrently, an amplitude sampling loop measures the active audio level and writes to `jarvisRealtimeRef.audioLevel`:
   ```typescript
   jarvisRealtimeRef.isSpeaking = true
   const audioInterval = setInterval(() => {
     if (!this.currentAudio || this.currentAudio.paused) {
       clearInterval(audioInterval)
       jarvisRealtimeRef.audioLevel = 0
       jarvisRealtimeRef.isSpeaking = false
       return
     }
     // Derive amplitude from AnalyserNode or volume envelope
     if (jarvisService?.analyser) {
       const data = new Uint8Array(64)
       jarvisService.analyser.getByteFrequencyData(data)
       let sum = 0
       for (let i = 0; i < 32; i++) sum += data[i]
       jarvisRealtimeRef.audioLevel = Math.min(1.0, (sum / (32 * 255)) * 1.8)
     }
   }, 33) // ~30 Hz sampling
   ```
3. **Zero-Re-Render Integrity**:
   Because updates are written directly to `jarvisRealtimeRef.audioLevel`, React does **not** re-render the DOM, allowing Three.js to consume the audio level inside `useFrame` at native display refresh rates (60–144 FPS).

---

## 7. Clean File Architecture & State Engine Blueprint

To cleanly decouple state arbitration, event listening, and UI subscriptions without causing re-render thrashing, the following modular architecture is designed:

```
src/components/dashboard/holographic-core/
├── types.ts                    # State definitions, weights, metadata
├── constants.ts                # Hex palettes, keymaps, ring geometries
├── geometries.ts               # Fibonacci sphere, Globe, Cube, Torus
├── procedural-textures.ts      # Canvas procedural glow and backdrop textures
├── audio-bridge.ts             # 3-band FFT analyzer and cadence fallback
├── state-machine.ts            # Damping transitions, cardiac beat, weights
├── state-arbitrator.ts         # [NEW] 7-Level Priority hierarchy, dwell & timeout manager
├── keyboard-controller.ts      # [NEW] Hotkeys 1-0,- with input & modifier guards
├── use-visualizer-state.ts     # [NEW] useSyncExternalStore micro-store for React UI
├── holographic-core-scene.tsx  # 4-layer Three.js canvas & render loop
└── index.ts                    # Public barrel export
```

### 7.1 Blueprint: `state-arbitrator.ts`

```typescript
/**
 * StateArbitrator: Deterministic 7-level priority hierarchy, tool mapping,
 * dwell time tracking, and fallback timeout management for the Holographic Core.
 */
import type { HolographicState, SphereProps } from './types'
import { normalizeStateName } from './state-machine'

export const PRIORITY_RANKS: Record<HolographicState, number> = {
  ALERT: 70,
  VISION_SCAN: 60,
  SPEAKING: 50,
  WEB_SEARCH: 40,
  DEEP_RESEARCH: 40,
  CODING: 40,
  MEMORY_SYNC: 40,
  EXECUTING_TOOL: 40,
  THINKING: 30,
  LISTENING: 20,
  IDLE: 10,
}

export class VisualizerStateArbitrator {
  private activeToolState: HolographicState | null = null
  private toolStartedAt: number = 0
  private toolDwellUntil: number = 0
  private readonly toolDwellDurationMs: number = 2000
  private readonly toolTimeoutDurationMs: number = 20000

  private alertDwellUntil: number = 0
  private readonly alertDwellDurationMs: number = 4000

  private lastResolvedState: HolographicState = 'IDLE'

  public onToolStart(toolName: string): HolographicState {
    const mapped = this.classifyTool(toolName)
    this.activeToolState = mapped
    this.toolStartedAt = Date.now()
    this.toolDwellUntil = 0
    return mapped
  }

  public onToolResult(): void {
    if (this.activeToolState) {
      this.toolDwellUntil = Date.now() + this.toolDwellDurationMs
    }
  }

  public triggerAlert(): void {
    this.alertDwellUntil = Date.now() + this.alertDwellDurationMs
  }

  public classifyTool(toolName: string | null | undefined): HolographicState {
    if (!toolName || typeof toolName !== 'string') return 'EXECUTING_TOOL'
    const tool = toolName.toLowerCase().trim()

    // Match DEEP_RESEARCH before WEB_SEARCH to prevent 'gpt_researcher' collision
    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
    if (/code|terminal|bash|edit|exec|shell|markdown|markitdown/i.test(tool)) return 'CODING'
    if (/vision|camera|scan|face|lidar|omni/i.test(tool)) return 'VISION_SCAN'
    if (/memory|db|store|sync|recall|session/i.test(tool)) return 'MEMORY_SYNC'
    return 'EXECUTING_TOOL'
  }

  public resolve(
    props: SphereProps,
    eventBusState?: string | null,
    realtimeVoiceState?: string | null,
    isVideoActive?: boolean
  ): HolographicState {
    const now = Date.now()

    // Level 1 Override: Explicit props.overrideState or props.state
    const explicit = props.overrideState ?? props.state
    if (explicit) {
      const normalized = normalizeStateName(String(explicit))
      if (normalized) return normalized
    }

    // Level 7: ALERT
    if (props.error || now < this.alertDwellUntil) {
      return 'ALERT'
    }

    // Level 6: VISION_SCAN
    if (isVideoActive || (props as any).isVideoOn) {
      return 'VISION_SCAN'
    }

    // Level 5: SPEAKING
    if (props.isSpeaking || realtimeVoiceState === 'SPEAKING' || eventBusState === 'SPEAKING') {
      return 'SPEAKING'
    }

    // Level 4: ACTIVE_TOOL with Dwell & Timeout Management
    if (this.activeToolState) {
      const isTimedOut = now - this.toolStartedAt > this.toolTimeoutDurationMs
      const isDwellExpired = this.toolDwellUntil > 0 && now > this.toolDwellUntil

      if (isTimedOut || isDwellExpired) {
        this.activeToolState = null
        this.toolDwellUntil = 0
      } else {
        return this.activeToolState
      }
    }

    if (props.activeTool) {
      return this.classifyTool(props.activeTool)
    }

    // Level 3: THINKING
    if (props.isThinking || realtimeVoiceState === 'THINKING' || eventBusState === 'THINKING') {
      return 'THINKING'
    }

    // Level 2: LISTENING
    if (props.isListening || realtimeVoiceState === 'LISTENING' || eventBusState === 'LISTENING') {
      return 'LISTENING'
    }

    // Realtime bus fallback
    if (eventBusState) {
      const normalized = normalizeStateName(eventBusState)
      if (normalized) return normalized
    }

    // Level 1: Default IDLE
    return 'IDLE'
  }
}
```

### 7.2 Blueprint: `keyboard-controller.ts`

```typescript
/**
 * KeyboardController: Encapsulates numeric hotkeys 1-0,- with strict guards
 * against input focus, contenteditable elements, and modifier keys.
 */
import { KEY_STATE_MAP } from './constants'
import type { HolographicState } from './types'

export class VisualizerKeyboardController {
  private listener: ((e: KeyboardEvent) => void) | null = null

  public attach(onStateSelect: (state: HolographicState) => void): () => void {
    this.listener = (e: KeyboardEvent) => {
      // Guard 1: Modifier keys
      if (e.ctrlKey || e.altKey || e.metaKey) return

      // Guard 2: Form inputs
      const target = e.target as HTMLElement | null
      if (!target) return
      const tag = target.tagName?.toUpperCase()
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

      // Guard 3: Contenteditable & rich text editors
      if (target.isContentEditable) return
      if (target.closest && target.closest('[contenteditable="true"], [contenteditable=""], [contenteditable]')) return
      if (target.closest && target.closest('.monaco-editor, .xterm, [role="textbox"]')) return

      const mapped = KEY_STATE_MAP[e.key]
      if (mapped) {
        onStateSelect(mapped)
        window.dispatchEvent(
          new CustomEvent('jarvis-state', { detail: { state: mapped } })
        )
      }
    }

    window.addEventListener('keydown', this.listener)
    return () => this.detach()
  }

  public detach(): void {
    if (this.listener) {
      window.removeEventListener('keydown', this.listener)
      this.listener = null
    }
  }
}
```

### 7.3 Blueprint: `use-visualizer-state.ts` (Zero-Thrash React Hook)

```typescript
/**
 * useVisualizerState: High-performance micro-store hook using useSyncExternalStore.
 * Triggers React component re-renders ONLY when the discrete HolographicState changes.
 * Never triggers re-renders on continuous 60 FPS audio amplitude changes.
 */
import { useSyncExternalStore } from 'react'
import type { HolographicState } from './types'
import { unpackJarvisStateDetail } from './state-machine'

let currentState: HolographicState = 'IDLE'
const listeners = new Set<() => void>()

function emitChange(nextState: HolographicState) {
  if (nextState !== currentState) {
    currentState = nextState
    listeners.forEach((l) => l())
  }
}

// Global window event listener initialization (singleton)
if (typeof window !== 'undefined') {
  window.addEventListener('jarvis-state', (e: Event) => {
    const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
    if (unpacked) emitChange(unpacked)
  })
}

export function setVisualizerState(state: HolographicState): void {
  emitChange(state)
}

export function useVisualizerState(): HolographicState {
  return useSyncExternalStore(
    (callback) => {
      listeners.add(callback)
      return () => listeners.delete(callback)
    },
    () => currentState,
    () => 'IDLE'
  )
}
```

---

## 8. Verification Plan & Test Matrix

To independently verify the Milestone 2 implementation, the following automated test suites must be executed:

### 8.1 Empirical Test Cases Matrix

| Test Suite | File | Focus | Assertions |
| :--- | :--- | :--- | :--- |
| **Priority Arbitration Suite** | `tests/test_m2_priority_arbitration.ts` | Verify $\text{ALERT} > \text{VISION} > \text{SPEAK} > \text{TOOL} > \text{THINK} > \text{LISTEN} > \text{IDLE}$ across all permutations | 45 assertions |
| **Dwell & Timeout Suite** | `tests/test_m2_dwell_timeouts.ts` | Verify 2000ms tool dwell, 20s hang timeout, 4000ms alert decay | 20 assertions |
| **CustomEvent Payload Suite** | `tests/test_m2_customevent_payloads.ts` | Test object payloads, string primitives, nested envelopes, aliases | 25 assertions |
| **Keyboard & Guard Suite** | `tests/test_m2_keyboard_guards.ts` | Verify keys `1`-`0`, `-` work when focused on canvas, and are ignored when in `<input>`, `<textarea>`, `contenteditable`, and with `Ctrl/Alt/Meta` | 30 assertions |
| **Audio Reactivity Suite** | `tests/test_m2_audio_reactivity.ts` | Verify `jarvisRealtimeRef.audioLevel` updates during TTS and mic input | 15 assertions |

### 8.2 Verification Commands

```powershell
# 1. Run Vitest Unit Tests
npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts

# 2. Run TypeScript Compilation
npm run typecheck

# 3. Run Production Build Verification
npx vite build
```

---

## 9. Conclusion

The investigation concludes that the 3D Holographic Core Visualizer is architecturally ready for Milestone 2 wiring. By implementing the 7-level state arbitrator with dwell/timeout management, polymorphic `jarvis-state` CustomEvent unpacking, keyboard hotkey guards, and TTS audio level streaming into `jarvisRealtimeRef.audioLevel`, the visualizer will react dynamically to all application and agent runtime events without frame drops or re-render thrashing.
