# Technical Investigation Report: Visualizer State & Event Wiring (Milestone 2)

**Author**: Explorer 1 (`explorer_m2_1`)  
**Date**: November 11, 2026  
**Target Milestone**: Milestone 2 — Visualizer State & Event Wiring  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App`  
**Target Output**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_1\report.md`  

---

## 1. Executive Summary

Milestone 1 successfully delivered the modular 3D Holographic Core Visualizer under `src/components/dashboard/holographic-core/` and re-exported it through `src/components/dashboard/sphere.tsx`, achieving 100% mathematical fidelity with `j_a_r_v_i_s_11_state_3d_holographic_core_visualizer.html`.

The objective of **Milestone 2 (Visualizer State & Event Wiring)** is to connect all 11 core holographic states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`) to the Electron application's runtime event pipeline. This encompasses:
1. Ingesting WebSocket events from `gatewayClient` (`/ws/jarvis`) and `jarvisBridge` (`/ws`).
2. Correcting and handling `agent.state` transitions (`idle`, `listening`, `thinking`, `speaking`, `transcribing`, `compressing`), wake word triggers (`wake_word_detected`), and TTS audio playback lifecycles.
3. Classifying tool execution events (`tool.start`, `tool.result`, `activeTool`) across the 5 specialized tool domains (`WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`) and generic `EXECUTING_TOOL`.
4. Detecting security violations, `AgentShield` policy blocks, and `confirmation_request` prompts to elevate to `ALERT`.
5. Enforcing a strict priority arbitration hierarchy (`ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE`) with state dwell times and safety fallback timeouts.
6. Providing interactive testing via `window.dispatchEvent(new CustomEvent('jarvis-state', ...))` and numeric keyboard hotkeys (`1`-`0`, `-`) in `src/pages/dashboard.tsx` guarded against inputs/textareas.

---

## 2. Codebase Investigation: Event Pipeline & Gateways

### 2.1 Gateway Client (`src/lib/gateway-client.ts`)
The `JarvisGatewayClient` establishes a full-duplex WebSocket connection to `ws://127.0.0.1:8765/ws/jarvis`, implementing the unified contract defined in `src/shared/protocol.ts`.

#### Observations in `src/lib/gateway-client.ts`:
- **`agent.state` (Lines 226-230)**:
  ```typescript
  else if (type === 'agent.state' || type === 'agent_state') {
    const stateVal = (payload.state || msg.state || '').toUpperCase();
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: stateVal }));
    this.stateListeners.forEach((listener) => listener(stateVal));
  }
  ```
  *Status*: Dispatches uppercase string primitive. Does not handle fine-grained mappings like `transcribing` or `compressing` directly, but passes them to DOM.
- **`tool.start` (Lines 260-265)**:
  ```typescript
  else if (type === 'tool.start' || type === 'tool_call_start') {
    const toolName = payload.tool || msg.tool;
    const toolArgs = payload.arguments || msg.arguments || {};
    this.toolListeners.forEach((listener) => listener({ phase: 'start', tool: toolName, arguments: toolArgs }));
    window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'start', tool: toolName, arguments: toolArgs } }));
  }
  ```
  *Defect / Gap*: `tool.start` only dispatches `jarvis-tool-call`. It currently **does not** dispatch `jarvis-state`, nor does it classify the tool into `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, or `MEMORY_SYNC`.
- **`tool.result` (Lines 268-277)**:
  ```typescript
  else if (type === 'tool.result' || type === 'tool_call_result') {
    const toolName = payload.tool || msg.tool;
    const toolRes = payload.result !== undefined ? payload.result : msg.result;
    const dur = payload.duration_ms;
    this.toolListeners.forEach((listener) => listener({ phase: 'result', tool: toolName, result: toolRes, duration_ms: dur }));
    window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'result', tool: toolName, result: toolRes, duration_ms: dur } }));
  }
  ```
  *Defect / Gap*: It does not inspect `payload.outcome === 'DENIED'` or check if the result indicates an `AgentShield` security block (`PermissionError`). Furthermore, upon normal tool completion, it does not transition the visualizer back to `THINKING` or `IDLE`.
- **`tts_playback` (Lines 329-332, 378-404)**:
  ```typescript
  else if (type === 'tts_playback') {
    window.dispatchEvent(new CustomEvent('jarvis-tts', { detail: msg }));
    this.playTtsAudio(msg.audioBase64, msg.mimeType);
  }
  ```
  In `playTtsAudio()`:
  - Dispatches `jarvis-state: 'SPEAKING'` immediately before playback.
  - On `audio.onended`, dispatches `jarvis-state: 'IDLE'`.
  - On `audio.onerror` or catch, dispatches `jarvis-state: 'IDLE'`.
  *Status*: Fully operational lifecycle, but does not feed audio amplitude into `jarvisRealtimeRef.audioLevel`.
- **`confirmation_request` (Lines 310-321)**:
  ```typescript
  else if (type === 'confirmation_request') {
    this.confirmationListeners.forEach((listener) =>
      listener({
        confirmationId: msg.confirmationId,
        toolName: msg.toolName,
        riskLevel: msg.riskLevel,
        arguments: msg.arguments,
        timeoutSeconds: msg.timeoutSeconds,
        timestamp: msg.timestamp
      })
    );
  }
  ```
  *Defect / Gap*: When a security confirmation request arrives, it alerts the UI modal (`ConfirmationModal.tsx`), but **does not** dispatch `jarvis-state: 'ALERT'`.
- **`wake_word_detected`**:
  *Defect / Gap*: There is no handler in `gateway-client.ts` for `wake_word_detected`.

---

### 2.2 High-Speed Bridge (`src/services/jarvisBridge.ts`)
The `JarvisBridge` client connects to `ws://127.0.0.1:8765/ws`.

#### Observations in `src/services/jarvisBridge.ts`:
- **Mutable Reference Store (Lines 71-76)**:
  ```typescript
  export const jarvisRealtimeRef = {
    audioLevel: 0,
    voiceState: 'IDLE' as string,
    isSpeaking: false,
    isListening: false,
  };
  ```
  This mutable store is directly read by `AudioReactivityBridge` in `audio-bridge.ts` during R3F `useFrame` at 60 FPS without React re-renders.
- **Voice State & Amplitude Ingestion (Lines 157-170)**:
  ```typescript
  else if (type === 'voice_state' || type === 'agent.state') {
    const vs = data as VoiceStateEnvelope;
    const amp = typeof vs.amplitude === 'number' ? vs.amplitude : 0;
    const state = (vs.state || 'IDLE').toUpperCase();

    jarvisRealtimeRef.audioLevel = amp;
    jarvisRealtimeRef.voiceState = state;
    jarvisRealtimeRef.isSpeaking = vs.is_speaking ?? (state === 'SPEAKING');
    jarvisRealtimeRef.isListening = state === 'LISTENING';

    this.voiceStateListeners.forEach((l) => l(vs));
    window.dispatchEvent(new CustomEvent('jarvis-voice-state', { detail: vs }));
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: state }));
  }
  ```
  *Status*: Fully updates `jarvisRealtimeRef` and dispatches `jarvis-state`.

---

### 2.3 Voice AI Service (`src/services/jarvis-voice-ai.ts`)
The `GeminiLiveService` connects to Web Audio API and maintains a secondary voice WebSocket.

#### Critical Bug Observed at Line 95-98:
```typescript
if (data.event === 'wake_word_detected' || data.type === 'wake_word_detected') {
  console.log('[jarvis-voice] Wake word detected:', data.wake_word)
  window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'SPEAKING' }))
  this.sendTextCommand('JARVIS, I am listening.')
}
```
**Defect D1**: When the wake word ("Hey Jarvis") is detected, line 97 dispatches `jarvis-state: 'SPEAKING'`. This is semantically incorrect: wake word detection means the user has initiated speech and the assistant is actively **listening**. It must dispatch `jarvis-state: 'LISTENING'`.

---

### 2.4 Dashboard Page (`src/pages/dashboard.tsx`)

#### Observations in `src/pages/dashboard.tsx`:
1. **`<Sphere />` Call Sites (Lines 606 & 695)**:
   ```tsx
   {/* Focus Mode */}
   <div className="w-[84vmin] h-[84vmin] ... pointer-events-none">
     <Sphere />
   </div>
   ...
   {/* Main Dashboard */}
   <div className="w-[60vh] h-[60vh] ... pointer-events-none">
     <Sphere />
   </div>
   ```
   Both call sites render `<Sphere />` without passing any state or tool props!
2. **`activeTool` State Tracking (Lines 375-388)**:
   ```typescript
   const [activeTool, setActiveTool] = useState<{ tool: string; phase: 'start' | 'result' } | null>(null)

   useEffect(() => {
     const handleTool = (e: any) => {
       if (e.detail) {
         setActiveTool({ tool: e.detail.tool, phase: e.detail.phase })
         if (e.detail.phase === 'result') {
           setTimeout(() => setActiveTool(null), 3000)
         }
       }
     }
     window.addEventListener('jarvis-tool-call', handleTool)
     return () => window.removeEventListener('jarvis-tool-call', handleTool)
   }, [])
   ```
   `dashboard.tsx` already captures `jarvis-tool-call`, but currently does not forward `activeTool={activeTool?.tool}` to `<Sphere />`.
3. **Keyboard Shortcuts in Dashboard**:
   `src/pages/dashboard.tsx` currently only listens for `Escape` in focus mode (line 328). It does not contain the Milestone 2 required numeric keyboard shortcuts (`1`-`0`, `-`).
4. **Vision Mode Tracking**:
   `dashboard.tsx` receives `isVideoOn` and `visionMode` from `JarvisProps`. When `isVideoOn` is true, the visualizer should reflect `VISION_SCAN`.

---

## 3. Tool Execution Event Classifier Analysis

### 3.1 Mapping Specifications
The requirements dictate the following exact tool classification:

| Target Holographic State | Tool Pattern / Name Matchers | Examples |
|---|---|---|
| **`WEB_SEARCH`** | `crawl4ai_*`, `browser_use_*`, `/search`, `google`, `browse`, `web` | `crawl4ai_extract`, `browser_use_background`, `/search?q=...` |
| **`DEEP_RESEARCH`** | `gpt_researcher_*`, `delegate_task`, `research`, `analyze`, `investigate` | `gpt_researcher_report`, `delegate_task` |
| **`CODING`** | `markitdown_*`, `code_*`, terminal execution, `bash`, `edit`, `exec`, `shell` | `markitdown_convert`, `code_interpreter`, `terminal_exec` |
| **`VISION_SCAN`** | `camera_*`, `mediapipe_*`, `deepface_*`, `vision_*`, `agent_s3_*`, `windows_mcp_snapshot`, or UI `isVideoOn` | `camera_hub_snap`, `mediapipe_landmarks`, `deepface_verify` |
| **`MEMORY_SYNC`** | `memory_*`, `state_db_*`, `saveCoreMemory`, `retrieveCoreMemory`, `core_memory` | `memory_store`, `state_db_vacuum`, `saveCoreMemory` |
| **`EXECUTING_TOOL`** | Any other tool identifier | `windows_mcp_click`, `mobilerun_phone_task`, `todo_create` |

### 3.2 Defect in Current Classifier
In `src/components/dashboard/holographic-core/state-machine.ts` (lines 90-99):
```typescript
if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
  const tool = props.activeTool.toLowerCase()
  if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
  if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
  if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
  if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
  if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
  return 'EXECUTING_TOOL'
}
```
**Defects Identified**:
1. `markitdown_convert` does NOT match `/code|terminal|bash|edit|exec|shell/i`. It falls through to `EXECUTING_TOOL` instead of `CODING`.
2. `mediapipe_*` does NOT match `/vision|camera|scan|face|lidar/i`. It falls through to `EXECUTING_TOOL` instead of `VISION_SCAN`.
3. `deepface_*` only matches because of `face`, but `mediapipe` does not.
4. Specific prefix matching (`crawl4ai_*`, `browser_use_*`, `gpt_researcher_*`, `state_db_*`, `saveCoreMemory`, `retrieveCoreMemory`) is only partially supported by substring matching.

### 3.3 Proposed Canonical Tool Classifier Function
```typescript
/**
 * Classifies any tool name or command string into its corresponding HolographicState.
 */
export function classifyToolState(toolName: string | null | undefined): HolographicState {
  if (!toolName || typeof toolName !== 'string') return 'EXECUTING_TOOL'
  const tool = toolName.trim().toLowerCase()

  // 1. DEEP_RESEARCH (checked before WEB_SEARCH to prevent 'researcher' from matching 'search')
  if (/^(gpt_researcher|delegate_task)|research|delegate|analyze|investigate/i.test(tool)) {
    return 'DEEP_RESEARCH'
  }

  // 2. WEB_SEARCH
  if (/^(crawl4ai|browser_use|\/search)|search|browse|crawl|google|web/i.test(tool)) {
    return 'WEB_SEARCH'
  }

  // 3. CODING
  if (/^(markitdown|code_)|markitdown|code|terminal|bash|edit|exec|shell|write_file/i.test(tool)) {
    return 'CODING'
  }

  // 4. VISION_SCAN
  if (/^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)|vision|camera|scan|face|lidar|mediapipe|deepface/i.test(tool)) {
    return 'VISION_SCAN'
  }

  // 5. MEMORY_SYNC
  if (/^(memory|state_db|savecorememory|retrievecorememory)|memory|state_db|savecore|retrievecore|store|sync|recall/i.test(tool)) {
    return 'MEMORY_SYNC'
  }

  // 6. Generic Fallback
  return 'EXECUTING_TOOL'
}
```

---

## 4. Security Violations, AgentShield & Confirmation Ingestion

### 4.1 Ingestion Sources for `ALERT`

```
+-------------------------------------------------------------------------+
|                         ALERT INGESTION CHANNELS                        |
+-------------------------------------------------------------------------+
| 1. confirmation_request (HIGH / CRITICAL / Medium)                      |
|       ==> Elevated tool gating requiring user authorization             |
|                                                                         |
| 2. tool.result with outcome === 'DENIED' or 'ERROR'                      |
|       ==> AgentShield policy block / PermissionError                    |
|                                                                         |
| 3. error / chat:error with critical/fatal security message               |
|       ==> Security breach / prompt injection / unauthorized command     |
|                                                                         |
| 4. Hardware Telemetry Alarms                                            |
|       ==> battery_percent < 10% & discharging                           |
|       ==> cpu_temp > 85°C (thermal throttling)                          |
|                                                                         |
| 5. Direct window CustomEvent: { detail: 'ALERT' }                       |
|       ==> Testing hotkey [-] or explicit security subsystem            |
+-------------------------------------------------------------------------+
```

### 4.2 Lifecycle & Auto-Dismissal
- When a `confirmation_request` is received, the visualizer enters `ALERT` (twin-beat lub-dub cardiac shockwave, `#fb7185`).
- When the user approves or denies the request via `ConfirmationModal`, or the 30-second timeout expires, `gatewayClient` sends `confirmation_response`. The state manager clears `ALERT` and returns to `THINKING` (if execution continues) or `IDLE`.
- When an `AgentShield` block occurs, `ALERT` dwells for **5.0 seconds** before automatically reverting to `IDLE` or `THINKING`, allowing the user to clearly see the red alert warning.

---

## 5. State Priority Arbitration Engine & Dwell Mechanics

### 5.1 Strict Priority Hierarchy
Per `SCOPE.md` and master specification:

$$\text{ALERT} (100) > \text{VISION\_SCAN} (90) > \text{SPEAKING} (80) > \text{ACTIVE\_TOOL} (70) > \text{THINKING} (60) > \text{LISTENING} (50) > \text{IDLE} (10)$$

Where `ACTIVE_TOOL` encompasses:
- `WEB_SEARCH`
- `DEEP_RESEARCH`
- `CODING`
- `MEMORY_SYNC`
- `EXECUTING_TOOL`

### 5.2 Resolution Logic Implementation
Currently, `resolveActiveState` in `state-machine.ts` resolves:
1. `overrideState ?? state`
2. `error`
3. `activeTool`
4. `isSpeaking`, `isThinking`, `isListening`
5. `realtimeVoiceState`
6. `IDLE`

**Inversion Bug**: In the current code, `activeTool` is checked *before* `isSpeaking` and before `realtimeVoiceState`. This means if a tool is executing while the assistant begins speaking (e.g., streaming status update), the visualizer stays in tool mode instead of transitioning to `SPEAKING`!
Furthermore, `VISION_SCAN` (`isVideoOn`) was not factored into priority arbitration.

### 5.3 Corrected Arbitration Hierarchy
```typescript
export function resolveActiveState(
  props: SphereProps,
  realtimeVoiceState?: string | null
): HolographicState {
  // Level 1: Explicit Override (highest precedence for manual testing & testing hotkeys)
  const explicit = props.overrideState ?? props.state
  if (explicit) {
    const normalized = normalizeStateName(String(explicit))
    if (normalized) return normalized
  }

  // Level 2: ALERT (Priority 100)
  if (props.error) return 'ALERT'
  const normalizedRealtime = normalizeStateName(realtimeVoiceState)
  if (normalizedRealtime === 'ALERT') return 'ALERT'

  // Level 3: VISION_SCAN (Priority 90)
  if (props.isVideoOn || props.visionActive) return 'VISION_SCAN'
  if (normalizedRealtime === 'VISION_SCAN') return 'VISION_SCAN'

  // Level 4: SPEAKING (Priority 80)
  if (props.isSpeaking || normalizedRealtime === 'SPEAKING') return 'SPEAKING'

  // Level 5: ACTIVE_TOOL (Priority 70)
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    return classifyToolState(props.activeTool)
  }
  if (
    normalizedRealtime === 'WEB_SEARCH' ||
    normalizedRealtime === 'DEEP_RESEARCH' ||
    normalizedRealtime === 'CODING' ||
    normalizedRealtime === 'MEMORY_SYNC' ||
    normalizedRealtime === 'EXECUTING_TOOL'
  ) {
    return normalizedRealtime
  }

  // Level 6: THINKING (Priority 60)
  if (props.isThinking || normalizedRealtime === 'THINKING') return 'THINKING'

  // Level 7: LISTENING (Priority 50)
  if (props.isListening || normalizedRealtime === 'LISTENING') return 'LISTENING'

  // Level 8: Realtime Voice Fallback or Default IDLE (Priority 10)
  if (normalizedRealtime) return normalizedRealtime
  return 'IDLE'
}
```

### 5.4 Dwell Times & Fallback Safety Timers
To ensure visual stability:
1. **Minimum Tool Dwell Time (400ms)**: When `tool.start` triggers a morph, hold the state for at least 400ms before allowing a revert to `THINKING` or `IDLE`, preventing flickering on sub-50ms tool executions.
2. **Alert Dwell Time (5000ms)**: Non-modal alerts linger for 5 seconds before returning to `IDLE`.
3. **Thinking Fallback (12000ms)**: If `THINKING` is triggered but no token chunks or tools arrive within 12 seconds, automatically revert to `IDLE`.
4. **Speaking Quiescence (1500ms)**: If in `SPEAKING` and audio has ceased for 1.5s without an explicit `IDLE` event, auto-revert to `IDLE`.

---

## 6. Interactive Verification & CustomEvent Specification

### 6.1 CustomEvent API Contract
The visualizer must listen for `jarvis-state` on `window`. To guarantee total interoperability, it supports both payload formats:
1. Object Payload:
   ```typescript
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'WEB_SEARCH' } }))
   ```
2. String Payload:
   ```typescript
   window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'WEB_SEARCH' }))
   ```
This is fully decoded by `unpackJarvisStateDetail()`.

### 6.2 Numeric Keyboard Shortcuts in `src/pages/dashboard.tsx`
Guarded by checking `target` against `HTMLInputElement`, `HTMLTextAreaElement`, `HTMLSelectElement`, and `isContentEditable`:

| Key | Target Holographic State | Visual Description |
|:---:|:---|:---|
| `1` | `IDLE` | Ice-Cyan calm breathing wave |
| `2` | `LISTENING` | Sky-Cyan inward contraction + sonar ripples |
| `3` | `THINKING` | Amber-Gold hemisphere twist vortex + gyroscopes |
| `4` | `SPEAKING` | White-Ice multi-band audio reactive corona |
| `5` | `WEB_SEARCH` | Cyber Azure 23.5° tilted globe + radar sweep |
| `6` | `DEEP_RESEARCH` | Periwinkle 3 nested counter-rotating shells |
| `7` | `CODING` | Matrix Mint beveled holo-cube + digital code |
| `8` | `VISION_SCAN` | Laser Rose sweeping lidar ring + laser plane |
| `9` | `MEMORY_SYNC` | Teal-Cyan Arc-Reactor torus + poloidal flow |
| `0` | `EXECUTING_TOOL` | Neon Violet multi-axis spin + octupole facets |
| `-` | `ALERT` | Crimson-Coral twin-beat cardiac shockwave |

---

## 7. Audio Streaming Integration

### 7.1 Multi-Source Audio Blending in `AudioReactivityBridge`
`audio-bridge.ts` aggregates:
1. `jarvisService.analyser`: Web Audio `AnalyserNode` connected to microphone stream (bins 0-15 bass, 16-55 mid, 56-111 treble).
2. `jarvisRealtimeRef.audioLevel`: Updated by WebSocket packets or TTS synthesis.
3. `propAudioLevel`: Passed via component props.
4. Autonomous speech cadence generator: Active when `SPEAKING` and input level $< 0.03$.
5. Attentive mic pulse: Active when `LISTENING` and input level $< 0.02$.

### 7.2 TTS Audio Amplitude Bridge
In `gatewayClient.playTtsAudio()`, when audio is playing, `jarvisRealtimeRef.isSpeaking` is set to `true`. By scheduling an amplitude envelope or hooking an `AudioContext` media element source, `jarvisRealtimeRef.audioLevel` can reflect speech modulation directly. Furthermore, the visualizer's built-in speech cadence generator acts as a seamless fallback.

---

## 8. Proposed Architecture & Implementation Plan

### 8.1 File Modifications Summary

```
src/
├── components/dashboard/
│   ├── sphere.tsx                              [Pass through extended props: isVideoOn, visionActive]
│   └── holographic-core/
│       ├── types.ts                            [Add isVideoOn?, visionActive? to SphereProps]
│       ├── state-machine.ts                    [Add classifyToolState(), update resolveActiveState() hierarchy]
│       └── holographic-core-scene.tsx          [Wire unpackJarvisStateDetail() in jarvis-state listener]
├── lib/
│   └── gateway-client.ts                       [Ingest tool.start/result, confirmation_request, wake_word_detected, DENIED -> ALERT]
├── services/
│   ├── jarvis-voice-ai.ts                      [Fix wake_word_detected: dispatch LISTENING instead of SPEAKING]
│   └── visualizer-state-coordinator.ts         [NEW: Unified State Coordinator with dwell & timeout management]
└── pages/
    └── dashboard.tsx                           [Add numeric keyboard shortcuts 1-0, -, wire activeTool and isVideoOn to <Sphere />]
```

### 8.2 Detailed Proposed Code Changes

#### 1. `src/components/dashboard/holographic-core/types.ts`
Add `isVideoOn` and `visionActive` to `SphereProps`:
```typescript
export interface SphereProps {
  count?: number
  state?: HolographicState | string | null
  overrideState?: HolographicState | string | null
  isListening?: boolean
  isSpeaking?: boolean
  isThinking?: boolean
  activeTool?: string | null
  isVideoOn?: boolean
  visionActive?: boolean
  error?: string | Error | null
  audioLevel?: number
  className?: string
  interactive?: boolean
  autoReturn?: boolean
}
```

#### 2. `src/components/dashboard/holographic-core/state-machine.ts`
Export `classifyToolState` and update `resolveActiveState`:
```typescript
/**
 * Classifies tool execution strings into one of the 11 HolographicStates.
 */
export function classifyToolState(toolName: string | null | undefined): HolographicState {
  if (!toolName || typeof toolName !== 'string') return 'EXECUTING_TOOL'
  const tool = toolName.trim().toLowerCase()

  // 1. DEEP_RESEARCH
  if (/^(gpt_researcher|delegate_task)|research|delegate|analyze|investigate/i.test(tool)) {
    return 'DEEP_RESEARCH'
  }
  // 2. WEB_SEARCH
  if (/^(crawl4ai|browser_use|\/search)|search|browse|crawl|google|web/i.test(tool)) {
    return 'WEB_SEARCH'
  }
  // 3. CODING
  if (/^(markitdown|code_)|markitdown|code|terminal|bash|edit|exec|shell|write_file/i.test(tool)) {
    return 'CODING'
  }
  // 4. VISION_SCAN
  if (/^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)|vision|camera|scan|face|lidar|mediapipe|deepface/i.test(tool)) {
    return 'VISION_SCAN'
  }
  // 5. MEMORY_SYNC
  if (/^(memory|state_db|savecorememory|retrievecorememory)|memory|state_db|savecore|retrievecore|store|sync|recall/i.test(tool)) {
    return 'MEMORY_SYNC'
  }
  return 'EXECUTING_TOOL'
}
```
Update `resolveActiveState`:
- Enforce strict order: `ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE`.
- Normalize backend state aliases `COMPRESSING` -> `THINKING`, `TRANSCRIBING` -> `THINKING`.

#### 3. `src/lib/gateway-client.ts`
- In `handleMessage(msg)`:
  - On `wake_word_detected`:
    ```typescript
    else if (type === 'wake_word_detected') {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'LISTENING' } }));
    }
    ```
  - On `tool.start`:
    ```typescript
    else if (type === 'tool.start' || type === 'tool_call_start') {
      const toolName = payload.tool || msg.tool;
      const toolArgs = payload.arguments || msg.arguments || {};
      this.toolListeners.forEach((l) => l({ phase: 'start', tool: toolName, arguments: toolArgs }));
      window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'start', tool: toolName, arguments: toolArgs } }));
      const mapped = classifyToolState(toolName);
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }));
    }
    ```
  - On `tool.result`:
    ```typescript
    else if (type === 'tool.result' || type === 'tool_call_result') {
      const toolName = payload.tool || msg.tool;
      const toolRes = payload.result !== undefined ? payload.result : msg.result;
      const dur = payload.duration_ms;
      const isDenied = payload.outcome === 'DENIED' || (typeof toolRes === 'string' && /AgentShield|PermissionError|blocked/i.test(toolRes));
      this.toolListeners.forEach((l) => l({ phase: 'result', tool: toolName, result: toolRes, duration_ms: dur }));
      window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'result', tool: toolName, result: toolRes, duration_ms: dur } }));
      if (isDenied) {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }));
      } else {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }));
      }
    }
    ```
  - On `confirmation_request`:
    ```typescript
    else if (type === 'confirmation_request') {
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }));
      // notify confirmation listeners...
    }
    ```

#### 4. `src/services/jarvis-voice-ai.ts`
Fix line 97:
```typescript
if (data.event === 'wake_word_detected' || data.type === 'wake_word_detected') {
  console.log('[jarvis-voice] Wake word detected:', data.wake_word)
  window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'LISTENING' } }))
  this.sendTextCommand('JARVIS, I am listening.')
}
```

#### 5. `src/pages/dashboard.tsx`
- Register numeric keyboard listeners `1`-`0`, `-`:
  ```typescript
  useEffect(() => {
    const handleVisualizerHotkeys = (e: KeyboardEvent) => {
      if (
        e.target &&
        (e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement ||
          e.target instanceof HTMLSelectElement ||
          (e.target as HTMLElement).isContentEditable)
      ) {
        return
      }
      const HOTKEY_MAP: Record<string, HolographicState> = {
        '1': 'IDLE',
        '2': 'LISTENING',
        '3': 'THINKING',
        '4': 'SPEAKING',
        '5': 'WEB_SEARCH',
        '6': 'DEEP_RESEARCH',
        '7': 'CODING',
        '8': 'VISION_SCAN',
        '9': 'MEMORY_SYNC',
        '0': 'EXECUTING_TOOL',
        '-': 'ALERT',
      }
      const mapped = HOTKEY_MAP[e.key]
      if (mapped) {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
      }
    }
    window.addEventListener('keydown', handleVisualizerHotkeys)
    return () => window.removeEventListener('keydown', handleVisualizerHotkeys)
  }, [])
  ```
- Wire props into `<Sphere />`:
  ```tsx
  <Sphere activeTool={activeTool?.tool} isVideoOn={isVideoOn} />
  ```

---

## 9. Verification Method & Test Plan

1. **Vitest Unit & Integration Tests**:
   Create a comprehensive test suite in `tests/test_milestone2_event_wiring.test.ts` (or in `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`):
   - **T1: Tool Classifier Coverage**: Verify all tool prefixes and keywords (`crawl4ai_*`, `browser_use_*`, `/search`, `gpt_researcher_*`, `delegate_task`, `markitdown_*`, `mediapipe_*`, `deepface_*`, `state_db_*`, `saveCoreMemory`, unknown tools) resolve to their respective 5 domains and generic fallback.
   - **T2: Priority Arbitration**: Verify `ALERT` beats `VISION_SCAN`, `VISION_SCAN` beats `SPEAKING`, `SPEAKING` beats `ACTIVE_TOOL`, `ACTIVE_TOOL` beats `THINKING`, `THINKING` beats `LISTENING`, and `LISTENING` beats `IDLE`.
   - **T3: CustomEvent Object & Primitive Unpacking**: Test `{ detail: { state: ... } }`, `{ detail: ... }`, and aliases.
   - **T4: Keyboard Shortcut Handler**: Test keys `1` through `0` and `-`, ensuring input elements are ignored.
   - **T5: Security & Confirmation Integration**: Test `confirmation_request` and `outcome: DENIED` producing `ALERT`.
2. **TypeScript Compilation**:
   ```powershell
   npm run typecheck
   ```
   *Expected*: Zero errors across all tsconfigs.
3. **Vite Production Build**:
   ```powershell
   npx vite build
   ```
   *Expected*: Zero errors, clean bundle output.

---
*End of Technical Investigation Report.*
