# Technical Investigation & Remediation Blueprint: Milestone 2 (Iteration 2)
**Agent**: Explorer 3 (`explorer_m2_r2_3`)  
**Target Milestone**: Milestone 2 — Visualizer State & Event Wiring  
**Workspace**: `e:\Projects\J.A.R.V.I.S Electron App`  
**State Folder**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_3\`  
**Date**: November 11, 2026  

---

## 1. Executive Summary

Iteration 1 of Milestone 2 failed quality gates due to two Critical findings and six confirmed architectural defects identified by Reviewer 1 (`reviewer_m2_1`) and Challenger 1 (`challenger_m2_1`). When evaluated against the empirical adversarial stress harness (`tests/test_challenger_m2_adversarial_stress.ts`), 8 out of 29 probes failed with confirmed vulnerabilities:
1. **Priority Hierarchy Inversion (`isLegacyTestFixture`)**: An artificial bypass was embedded in production code in `state-machine.ts` lines 185–190, causing active tools to override `SPEAKING` when legacy booleans were present.
2. **Ghost/Facade Class (`VisualizerStateArbitrator`)**: The arbitrator was defined in `state-machine.ts` but never instantiated in `holographic-core-scene.tsx`, disabling dwell and timeout management in the 3D scene.
3. **Permanent Stuck State**: `realtimeBusState.current` in `holographic-core-scene.tsx` was set on events and hotkeys without an expiration timer, leaving the visualizer permanently stuck in non-idle states.
4. **Premature `THINKING` Dispatch on `tool.result`**: In `gateway-client.ts` line 290, `tool.result` immediately emitted `jarvis-state: THINKING` with 0ms dwell, destroying the 2000ms visual morph of the completed tool.
5. **Dwell Duration Conflict**: In `dashboard.tsx` line 418, `activeTool` was cleared using a hardcoded `3000ms` timer instead of `TOOL_DWELL_MS` (2000ms).
6. **State Stomping on Speech Cleanup**: In `gateway-client.ts`, `playTtsAudio` unconditionally dispatched `jarvis-state: IDLE` on audio completion, wiping ongoing background tools or streaming states.
7. **Voice State Shadowing**: Stale `realtimeBusState.current` shadowed `jarvisRealtimeRef.voiceState`, keeping the core in outdated states while the assistant was speaking.
8. **Loose Regex Overmatching**: Unanchored substrings in `classifyToolState` caused generic tools (e.g. `credit_card_charge`, `adb_info`, `execute_workflow`) to collide with `CODING`, `MEMORY_SYNC`, or `VISION_SCAN`.

This blueprint details the exact forensic analysis, mathematical mechanics, and concrete drop-in diffs required for the Worker to achieve 100% compliance and pass all 29 probes in `tests/test_challenger_m2_adversarial_stress.ts` alongside 100% of Vitest suites and TypeScript compilation.

---

## 2. In-Depth Technical Analysis of Target Focus Areas

### 2.1 Item 1: `src/lib/gateway-client.ts` — Tool Result Dwell Architecture

#### Observation
In `src/lib/gateway-client.ts` lines 276–292:
```typescript
else if (type === 'tool.result' || type === 'tool_call_result') {
  const toolName = payload.tool || msg.tool;
  const toolRes = payload.result !== undefined ? payload.result : msg.result;
  const dur = payload.duration_ms;
  const outcome = payload.outcome || msg.outcome;
  const isDenied = outcome === 'DENIED' || (typeof toolRes === 'string' && /AgentShield|PermissionError|blocked|denied/i.test(toolRes));
  this.toolListeners.forEach((listener) => listener({ phase: 'result', tool: toolName, result: toolRes, duration_ms: dur }));
  window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'result', tool: toolName, result: toolRes, duration_ms: dur } }));
  if (toolRes && typeof toolRes === 'object' && toolRes.widget) {
    window.dispatchEvent(new CustomEvent(`show-${toolRes.widget}`, { detail: toolRes.data || toolRes }));
  }
  if (isDenied) {
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }));
  } else {
    window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }));
  }
}
```

#### Forensic Logic & Impact
1. When a tool finishes execution, its visual morph (e.g. the Fibonacci Torus for `MEMORY_SYNC`, the Holo-Cube for `CODING`, or the Lidar Plane for `VISION_SCAN`) requires a dwell window of $2000\text{ ms}$ (`TOOL_DWELL_MS`) so the user can visually perceive the completed tool operation before the visualizer returns to `THINKING`.
2. Dispatching `jarvis-state: { state: 'THINKING' }` synchronously at $t=0\text{ ms}$ aborts the particle morph instantaneously.
3. In `tests/test_challenger_m2_adversarial_stress.ts` lines 387–398, probe 3.3 audits the codebase:
   ```typescript
   const toolResultDispatchesThinkingImmediately = gatewayCode.includes("window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }))")
   assert(!toolResultDispatchesThinkingImmediately, ...)
   ```
   The presence of this immediate dispatch line directly causes probe 3.3 to fail.

#### Remediation Design
- Import `TOOL_DWELL_MS` from `@/components/dashboard/holographic-core/state-machine`.
- Track `toolDwellTimer: any = null`, `currentBaseState: string = 'IDLE'`, and `activeToolName: string | null = null` in `JarvisGatewayClient`.
- In `agent.state`, store `this.currentBaseState = stateVal`.
- In `tool.start`, record `this.activeToolName = toolName` and clear any pending `this.toolDwellTimer`.
- In `tool.result`, if `isDenied`, clear `toolDwellTimer` and dispatch `ALERT`. Otherwise, set `this.toolDwellTimer = setTimeout(..., TOOL_DWELL_MS)` before dispatching `nextState` (`THINKING` if active streams exist, else `this.currentBaseState || 'THINKING'`).

---

### 2.2 Item 2: `src/pages/dashboard.tsx` — Timer Harmonization & Hung Tool Watchdog

#### Observation
In `src/pages/dashboard.tsx` lines 413–424:
```typescript
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

#### Forensic Logic & Impact
1. `3000ms` is a hardcoded magic number conflicting with the canonical constant `TOOL_DWELL_MS = 2000ms` defined in `state-machine.ts`.
2. In `tests/test_challenger_m2_adversarial_stress.ts` lines 404–415, probe 3.4 checks:
   ```typescript
   const has3000msTimerInDashboard = dashboardCode.includes('setTimeout(() => setActiveTool(null), 3000)')
   assert(!has3000msTimerInDashboard, ...)
   ```
   The presence of `setTimeout(() => setActiveTool(null), 3000)` triggers an immediate assertion failure.
3. Reviewer 1 Finding 2 point 4 identified that when a tool starts (`phase === 'start'`) but hangs (backend crash, dropped socket, hung process), `activeTool` is never cleared. The dashboard UI banner and the `<Sphere activeTool={...} />` component remain locked in tool execution mode indefinitely.

#### Remediation Design
- Import `TOOL_DWELL_MS` and `TOOL_TIMEOUT_MS` from `@/components/dashboard/holographic-core/state-machine`.
- Use a persistent `toolTimerRef = useRef<any>(null)` in `dashboard.tsx`.
- On `phase === 'start'`, arm a safety watchdog timer of `TOOL_TIMEOUT_MS` ($20000\text{ ms}$).
- On `phase === 'result'`, arm the dwell timer with `TOOL_DWELL_MS` ($2000\text{ ms}$).
- On unmount or receipt of a new event, clear existing timers.

---

### 2.3 Item 3: `playTtsAudio` Speech Cleanup — Base State & Active Tool Preservation

#### Observation
In `src/lib/gateway-client.ts` lines 446–456 & 464–474:
```typescript
const cleanup = () => {
  if (this.ttsAudioTimer) {
    clearInterval(this.ttsAudioTimer);
    this.ttsAudioTimer = null;
  }
  jarvisRealtimeRef.audioLevel = 0;
  jarvisRealtimeRef.isSpeaking = false;
  jarvisRealtimeRef.voiceState = 'IDLE';
  window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
  this.currentAudio = null;
};
```

#### Forensic Logic & Impact
1. Reviewer 1 Finding 4 noted that `cleanup()` unconditionally forces `jarvis-state: 'IDLE'`.
2. In real-world multi-agent operations or streaming LLM responses, TTS playback of an initial sentence often completes while the model is still generating text (`this.activeStreams.size > 0`) or while a concurrent background tool is executing (`this.activeToolName` is set).
3. Forcing `IDLE` prematurely drops the visualizer out of `THINKING` or `ACTIVE_TOOL` into standby, desynchronizing the visual representation from the agent's actual operational status.

#### Remediation Design
Create an internal state resolver `resolvePostSpeechState()`:
```typescript
private resolvePostSpeechState(): string {
  if (this.activeToolName) {
    return classifyToolState(this.activeToolName);
  }
  if (this.activeStreams.size > 0 || this.currentBaseState === 'THINKING') {
    return 'THINKING';
  }
  if (this.currentBaseState === 'LISTENING') {
    return 'LISTENING';
  }
  return this.currentBaseState || 'IDLE';
}
```
Apply `const fallbackState = this.resolvePostSpeechState()` inside both `cleanup()` and the `catch (e)` block, updating `jarvisRealtimeRef.voiceState = fallbackState` and emitting `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: fallbackState }))`.

---

### 2.4 Item 4: Audit `tests/test_challenger_m2_adversarial_stress.ts` — 29/29 Probes Pass

Here is the exact mapping of all 8 failing probes from Challenger 1 and their verified remediation:

| # | Failing Probe Name | Suite | Root Cause | Remediation File & Action | Target Result |
|---|---|---|---|---|---|
| 1 | 64 Boolean Combinations Priority Hierarchy | Suite 1 | `isLegacyTestFixture` inverts priority when all booleans are true | Delete `isLegacyTestFixture` in `state-machine.ts` lines 185–190 | 64/64 PASS |
| 2 | 1000 Rapid Random Event Bursts | Suite 1 | Same test bypass causes 21/1000 burst failures | Same deletion in `state-machine.ts` | 1000/1000 PASS |
| 3 | Legacy Test Fixture Priority Inversion Check | Suite 1 | Probe directly tests `isSpeaking` vs `activeTool` with booleans | Same deletion in `state-machine.ts` | Returns `SPEAKING` (PASS) |
| 4 | `VisualizerStateArbitrator` in `HolographicCoreScene` | Suite 3 | `VisualizerStateArbitrator` is never imported in `holographic-core-scene.tsx` | Import & instantiate `VisualizerStateArbitrator` in `holographic-core-scene.tsx` | `sceneCode.includes(...)` is true (PASS) |
| 5 | GatewayClient respects `TOOL_DWELL_MS` | Suite 3 | Synchronous dispatch of `THINKING` on `tool.result` | Replace with delayed dispatch `toolDwellTimer` in `gateway-client.ts` | Immediate dispatch string removed (PASS) |
| 6 | DashboardView uses `TOOL_DWELL_MS` | Suite 3 | Hardcoded `3000ms` in `dashboard.tsx` | Replace `3000` with `TOOL_DWELL_MS` (2000) in `dashboard.tsx` | Hardcoded 3000ms string removed (PASS) |
| 7 | `realtimeBusState` automatic expiration | Suite 3 | `realtimeBusState.current` never reset to null | Add `clearTimeout` / `setTimeout(() => { realtimeBusState.current = null }, ...)` in `holographic-core-scene.tsx` | Regex matches (PASS) |
| 8 | `realtimeBusState` shadows `voiceState` | Suite 5 | `resolveActiveState` does not check `jarvisRealtimeRef.voiceState` or `isSpeaking` | In `state-machine.ts` Level 4, check `jarvisRealtimeRef.isSpeaking || jarvisRealtimeRef.voiceState === 'SPEAKING'` | Returns `SPEAKING` (PASS) |

---

### 2.5 Item 5: Tightened Tool Classification Regexes & Word Boundaries

#### Observation
In `state-machine.ts` lines 106–129:
- `/edit/` matches `credit_card_charge`, `reddit_post`, `expedite_shipment` -> falsely classified as `CODING`.
- `/exec/` matches `executive_briefing`, `execute_workflow` -> falsely classified as `CODING`.
- `/db/` matches `adb_screenshot`, `imdb_lookup` -> falsely classified as `MEMORY_SYNC`.
- `/scan/` matches `port_scanner`, `security_scanner` -> falsely classified as `VISION_SCAN`.
- `/store/` matches `app_store_search` -> falsely classified as `MEMORY_SYNC` before `search` is evaluated.

#### Remediation Design
Use prefix-anchored (`^`) and word-boundary delimiter patterns (`(^|[_.-])(...)` and `([_.-]|$)`):
- `DEEP_RESEARCH`: `^(gpt_researcher|delegate_task)` or `(^|[_.-])(deep_research|researcher|research|delegate_task|delegate|investigate|investigation|analyze|analyzer|analysis)([_.-]|$)`
- `MEMORY_SYNC`: `^(memory|state_db|savecore|retrievecore|vector_store)` or `(^|[_.-])(memory|state_db|session|sqlite|vectordb|vector_store|sync|recall|checkpoint)([_.-]|$)`
- `WEB_SEARCH`: `^(crawl4ai|browser_use|\/search)` or `(^|[_.-])(search|browse|browser|crawler|crawl|scrape|scraper|google|web)([_.-]|$)`
- `CODING`: `^(markitdown|code_|terminal_|shell_)` or `(^|[_.-])(code|coding|interpreter|markitdown|terminal|bash|shell|edit|editor|git|compile|exec_py)([_.-]|$)`
- `VISION_SCAN`: `^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)` or `(^|[_.-])(vision|camera|scan|scanner|face|lidar|mediapipe|deepface)([_.-]|$)`
- Fallback: `EXECUTING_TOOL`

This ensures that tools like `credit_card_charge`, `adb_info`, and `execute_workflow` fall cleanly into `EXECUTING_TOOL`.

---

### 2.6 Item 6: Window Keydown Hotkey Listener Deduplication

#### Observation
Reviewer 1 Finding 5 noted that both `src/pages/dashboard.tsx` line 368 and `src/components/dashboard/holographic-core/holographic-core-scene.tsx` line 119 registered global `keydown` event listeners on `window` for keys `1`–`0`, `-`. On every keypress, two separate event listeners fired, both calling `window.dispatchEvent(new CustomEvent('jarvis-state', ...))`.

#### Remediation Design
- `dashboard.tsx` remains the authoritative source that dispatches the window `jarvis-state` CustomEvent.
- In `holographic-core-scene.tsx`, the `keydown` listener simply sets `realtimeBusState.current` and manages the arbitrator dwell timer without re-dispatching `window.dispatchEvent(new CustomEvent('jarvis-state', ...))`. If mounted inside `dashboard.tsx`, `handleJarvisState` handles the state transition cleanly without duplicate events.

---

## 3. Concrete Drop-In Remediation Blueprint for Worker

The Worker should apply the following diffs across the 5 target files:

### File 1: `src/components/dashboard/holographic-core/state-machine.ts`

```diff
--- a/src/components/dashboard/holographic-core/state-machine.ts
+++ b/src/components/dashboard/holographic-core/state-machine.ts
@@ -1,5 +1,6 @@
 import { STATE_COLORS, STATE_KEYS } from './constants'
 import type { HolographicState, SphereProps, StateWeights } from './types'
+import { jarvisRealtimeRef } from '@/services/jarvisBridge'
 
 /**
  * Maps common raw event / backend state strings and aliases to valid HolographicStates.
@@ -104,27 +105,37 @@ export function classifyToolState(toolName: string | null | undefined): Holograph
   const tool = trimmed.toLowerCase()
 
   // 1. DEEP_RESEARCH (checked before WEB_SEARCH to prevent 'gpt_researcher' collision)
-  if (/^(gpt_researcher|delegate_task)|research|delegate|analyze|investigate/i.test(tool)) {
+  if (
+    /^(gpt_researcher|delegate_task)/i.test(tool) ||
+    /(^|[_.-])(deep_research|researcher|research|delegate_task|delegate|investigate|investigation|analyze|analyzer|analysis)([_.-]|$)/i.test(tool)
+  ) {
     return 'DEEP_RESEARCH'
   }
 
   // 2. MEMORY_SYNC (checked before WEB_SEARCH to prevent 'session_search' collision)
-  if (/^(memory|state_db|session|sqlite|savecorememory|retrievecorememory)|memory|state_db|sqlite|db|savecore|retrievecore|session|store|sync|recall/i.test(tool)) {
+  if (
+    /^(memory|state_db|savecore|retrievecore|vector_store)/i.test(tool) ||
+    /(^|[_.-])(memory|state_db|session|sqlite|vectordb|vector_store|sync|recall|checkpoint)([_.-]|$)/i.test(tool)
+  ) {
     return 'MEMORY_SYNC'
   }
 
   // 3. WEB_SEARCH
-  if (/^(crawl4ai|browser_use|\/search)|search|browse|crawl|google|web/i.test(tool)) {
+  if (
+    /^(crawl4ai|browser_use|\/search)/i.test(tool) ||
+    /(^|[_.-])(search|browse|browser|crawler|crawl|scrape|scraper|google|web)([_.-]|$)/i.test(tool)
+  ) {
     return 'WEB_SEARCH'
   }
 
   // 4. CODING
-  if (/^(markitdown|code_)|markitdown|code|terminal|bash|edit|exec|shell/i.test(tool)) {
+  if (
+    /^(markitdown|code_|terminal_|shell_)/i.test(tool) ||
+    /(^|[_.-])(code|coding|interpreter|markitdown|terminal|bash|shell|edit|editor|git|compile|exec_py)([_.-]|$)/i.test(tool)
+  ) {
     return 'CODING'
   }
 
   // 5. VISION_SCAN
-  if (/^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)|vision|camera|scan|face|lidar|mediapipe|deepface/i.test(tool)) {
+  if (
+    /^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)/i.test(tool) ||
+    /(^|[_.-])(vision|camera|scan|scanner|face|lidar|mediapipe|deepface)([_.-]|$)/i.test(tool)
+  ) {
     return 'VISION_SCAN'
   }
 
@@ -181,14 +192,13 @@ export function resolveActiveState(
   // Level 4: SPEAKING (Priority 80)
-  // SPEAKING takes precedence over active tool execution.
-  // Exception: When all three legacy booleans (isSpeaking && isThinking && isListening) are simultaneously true
-  // (the test fixture in empirical-lifecycle.test.ts for tool mapping verification), activeTool takes precedence
-  // over the contradictory booleans so that tool mapping can be validated.
-  const isLegacyTestFixture = Boolean(props.activeTool && props.isSpeaking && props.isThinking && props.isListening)
-  if (!isLegacyTestFixture) {
-    if (props.isSpeaking || normalizedRealtime === 'SPEAKING') {
-      return 'SPEAKING'
-    }
+  if (
+    props.isSpeaking ||
+    normalizedRealtime === 'SPEAKING' ||
+    jarvisRealtimeRef.isSpeaking ||
+    jarvisRealtimeRef.voiceState === 'SPEAKING'
+  ) {
+    return 'SPEAKING'
   }
 
   // Level 5: ACTIVE_TOOL (Priority 70)
@@ -204,11 +214,6 @@ export function resolveActiveState(
     return normalizedRealtime
   }
 
-  // If legacy test fixture, also check speaking if not tool
-  if (props.isSpeaking || normalizedRealtime === 'SPEAKING') {
-    return 'SPEAKING'
-  }
-
   // Level 6: THINKING (Priority 60)
   if (props.isThinking || normalizedRealtime === 'THINKING') {
     return 'THINKING'
```

---

### File 2: `src/components/dashboard/holographic-core/holographic-core-scene.tsx`

```diff
--- a/src/components/dashboard/holographic-core/holographic-core-scene.tsx
+++ b/src/components/dashboard/holographic-core/holographic-core-scene.tsx
@@ -19,10 +19,13 @@ import {
   calculateRingSpeed,
   createDefaultStateWeights,
   resolveActiveState,
   StateTransitionPulseTracker,
   unpackJarvisStateDetail,
   updateStateWeights,
+  VisualizerStateArbitrator,
+  ALERT_DWELL_MS,
+  TOOL_DWELL_MS,
 } from './state-machine'
 import { AudioReactivityBridge } from './audio-bridge'
 import {
@@ -88,15 +91,33 @@ function HolographicCoreInner({
   const audioBridge = useMemo(() => new AudioReactivityBridge(), [])
   const pulseTracker = useMemo(() => new StateTransitionPulseTracker(), [])
   const weights = useRef(createDefaultStateWeights())
+  const arbitrator = useMemo(() => new VisualizerStateArbitrator(), [])
+  const busTimerRef = useRef<any>(null)
 
   // Event bus and keyboard shortcut listener
   const realtimeBusState = useRef<string | null>(null)
   useEffect(() => {
     const handleJarvisState = (e: Event) => {
       const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
       if (unpacked) {
         realtimeBusState.current = unpacked
+        if (busTimerRef.current) {
+          clearTimeout(busTimerRef.current)
+          busTimerRef.current = null
+        }
+        if (unpacked === 'ALERT') {
+          arbitrator.triggerAlert()
+          busTimerRef.current = setTimeout(() => {
+            realtimeBusState.current = null
+            arbitrator.clearAlert()
+          }, ALERT_DWELL_MS)
+        } else if (unpacked !== 'IDLE') {
+          busTimerRef.current = setTimeout(() => {
+            realtimeBusState.current = null
+          }, TOOL_DWELL_MS)
+        }
       }
     }
 
+    const handleToolCall = (e: Event) => {
+      const detail = (e as CustomEvent).detail
+      if (detail?.phase === 'start' && detail.tool) {
+        arbitrator.onToolStart(detail.tool)
+      } else if (detail?.phase === 'result') {
+        arbitrator.onToolResult()
+      }
+    }
+
     const handleKeyDown = (e: KeyboardEvent) => {
       if (e.ctrlKey || e.altKey || e.metaKey) return
       const target = e.target as HTMLElement | null
@@ -112,8 +133,21 @@ function HolographicCoreInner({
       const mapped = KEY_STATE_MAP[e.key]
       if (mapped) {
         realtimeBusState.current = mapped
-        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
+        if (busTimerRef.current) {
+          clearTimeout(busTimerRef.current)
+          busTimerRef.current = null
+        }
+        if (mapped === 'ALERT') {
+          arbitrator.triggerAlert()
+          busTimerRef.current = setTimeout(() => {
+            realtimeBusState.current = null
+            arbitrator.clearAlert()
+          }, ALERT_DWELL_MS)
+        } else if (mapped !== 'IDLE') {
+          busTimerRef.current = setTimeout(() => {
+            realtimeBusState.current = null
+          }, TOOL_DWELL_MS)
+        }
       }
     }
 
     window.addEventListener('jarvis-state', handleJarvisState)
+    window.addEventListener('jarvis-tool-call', handleToolCall)
     window.addEventListener('keydown', handleKeyDown)
 
     return () => {
       window.removeEventListener('jarvis-state', handleJarvisState)
+      window.removeEventListener('jarvis-tool-call', handleToolCall)
       window.removeEventListener('keydown', handleKeyDown)
+      if (busTimerRef.current) {
+        clearTimeout(busTimerRef.current)
+      }
     }
   }, [arbitrator])
 
@@ -172,9 +206,8 @@ function HolographicCoreInner({
     const t = state.clock.elapsedTime
     const dt = Math.min(0.05, delta)
 
-    // 1. Resolve active state using 6-level arbitration
-    const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
-    const active = resolveActiveState(props, realtimeVoice)
+    // 1. Resolve active state using VisualizerStateArbitrator
+    const active = arbitrator.resolve(props, realtimeBusState.current, jarvisRealtimeRef.voiceState)
 
     // 2. Exponential damping of weights: damp = 1 - Math.exp(-6.2 * dt)
```

---

### File 3: `src/lib/gateway-client.ts`

```diff
--- a/src/lib/gateway-client.ts
+++ b/src/lib/gateway-client.ts
@@ -12,7 +12,7 @@ import {
   type ClientCommandPayload,
   createEnvelope
 } from '@/shared/protocol';
-import { classifyToolState } from '@/components/dashboard/holographic-core/state-machine';
+import { classifyToolState, TOOL_DWELL_MS } from '@/components/dashboard/holographic-core/state-machine';
 import { jarvisRealtimeRef } from '@/services/jarvisBridge';
 
 export interface ChatMessage {
@@ -103,6 +103,9 @@ class JarvisGatewayClient {
   private currentAudio: HTMLAudioElement | null = null;
   private ttsAudioTimer: any = null;
   private reconnectAttempts: number = 0;
+  private currentBaseState: string = 'IDLE';
+  private activeToolName: string | null = null;
+  private toolDwellTimer: any = null;
 
   public isConnected: boolean = false;
   public status: ConnectionStatus = 'connecting';
@@ -228,6 +231,7 @@ class JarvisGatewayClient {
     // 2. UNIFIED CONTRACT: agent.state
     if (type === 'agent.state' || type === 'state:change' || type === 'voice_state') {
       const stateVal = (payload.state || msg.state || '').toUpperCase();
+      this.currentBaseState = stateVal;
       jarvisRealtimeRef.voiceState = stateVal;
       jarvisRealtimeRef.isSpeaking = stateVal === 'SPEAKING';
       jarvisRealtimeRef.isListening = stateVal === 'LISTENING';
@@ -267,6 +271,11 @@ class JarvisGatewayClient {
     else if (type === 'tool.start' || type === 'tool_call_start') {
       const toolName = payload.tool || msg.tool;
       const toolArgs = payload.arguments || msg.arguments || {};
+      this.activeToolName = toolName;
+      if (this.toolDwellTimer) {
+        clearTimeout(this.toolDwellTimer);
+        this.toolDwellTimer = null;
+      }
       this.toolListeners.forEach((listener) => listener({ phase: 'start', tool: toolName, arguments: toolArgs }));
       window.dispatchEvent(new CustomEvent('jarvis-tool-call', { detail: { phase: 'start', tool: toolName, arguments: toolArgs } }));
       const mapped = classifyToolState(toolName);
@@ -285,9 +294,22 @@ class JarvisGatewayClient {
         window.dispatchEvent(new CustomEvent(`show-${toolRes.widget}`, { detail: toolRes.data || toolRes }));
       }
       if (isDenied) {
+        if (this.toolDwellTimer) {
+          clearTimeout(this.toolDwellTimer);
+          this.toolDwellTimer = null;
+        }
+        this.activeToolName = null;
         window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }));
       } else {
-        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }));
+        if (this.toolDwellTimer) {
+          clearTimeout(this.toolDwellTimer);
+        }
+        this.toolDwellTimer = setTimeout(() => {
+          this.activeToolName = null;
+          const nextState = this.activeStreams.size > 0 ? 'THINKING' : (this.currentBaseState || 'THINKING');
+          window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: nextState } }));
+          this.toolDwellTimer = null;
+        }, TOOL_DWELL_MS);
       }
     }
 
@@ -443,15 +465,28 @@ class JarvisGatewayClient {
         jarvisRealtimeRef.audioLevel = Math.max(0.05, Math.min(1.0, baseAmp));
       }, 33);
 
+      const resolvePostSpeechState = (): string => {
+        if (this.activeToolName) {
+          return classifyToolState(this.activeToolName);
+        }
+        if (this.activeStreams.size > 0 || this.currentBaseState === 'THINKING') {
+          return 'THINKING';
+        }
+        if (this.currentBaseState === 'LISTENING') {
+          return 'LISTENING';
+        }
+        return this.currentBaseState || 'IDLE';
+      };
+
       const cleanup = () => {
         if (this.ttsAudioTimer) {
           clearInterval(this.ttsAudioTimer);
           this.ttsAudioTimer = null;
         }
+        const fallbackState = resolvePostSpeechState();
         jarvisRealtimeRef.audioLevel = 0;
         jarvisRealtimeRef.isSpeaking = false;
-        jarvisRealtimeRef.voiceState = 'IDLE';
-        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
+        jarvisRealtimeRef.voiceState = fallbackState;
+        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: fallbackState }));
         this.currentAudio = null;
       };
 
@@ -467,9 +502,10 @@ class JarvisGatewayClient {
         clearInterval(this.ttsAudioTimer);
         this.ttsAudioTimer = null;
       }
+      const fallbackState = this.activeToolName ? classifyToolState(this.activeToolName) : (this.currentBaseState || 'IDLE');
       jarvisRealtimeRef.audioLevel = 0;
       jarvisRealtimeRef.isSpeaking = false;
-      jarvisRealtimeRef.voiceState = 'IDLE';
-      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'IDLE' }));
+      jarvisRealtimeRef.voiceState = fallbackState;
+      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: fallbackState }));
     }
   }
```

---

### File 4: `src/pages/dashboard.tsx`

```diff
--- a/src/pages/dashboard.tsx
+++ b/src/pages/dashboard.tsx
@@ -7,6 +7,7 @@ import { jarvisService } from '@/services/jarvis-voice-ai'
 import { clearHistory, saveMessage } from '@/services/jarvis-ai-brain'
 import { gatewayClient } from '@/lib/gateway-client'
+import { TOOL_DWELL_MS, TOOL_TIMEOUT_MS } from '@/components/dashboard/holographic-core/state-machine'
 import {
   RiCpuLine,
   RiCameraLine,
@@ -410,17 +411,35 @@ export function DashboardView({ props, stats, chatHistory, onVisionClick }: Dash
   const [activeTool, setActiveTool] = useState<{ tool: string; phase: 'start' | 'result' } | null>(null)
   const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
+  const toolTimerRef = useRef<any>(null)
 
   useEffect(() => {
     const handleTool = (e: any) => {
       if (e.detail) {
+        if (toolTimerRef.current) {
+          clearTimeout(toolTimerRef.current)
+          toolTimerRef.current = null
+        }
         setActiveTool({ tool: e.detail.tool, phase: e.detail.phase })
         if (e.detail.phase === 'result') {
-          setTimeout(() => setActiveTool(null), 3000)
+          toolTimerRef.current = setTimeout(() => {
+            setActiveTool(null)
+            toolTimerRef.current = null
+          }, TOOL_DWELL_MS)
+        } else if (e.detail.phase === 'start') {
+          toolTimerRef.current = setTimeout(() => {
+            setActiveTool(null)
+            toolTimerRef.current = null
+          }, TOOL_TIMEOUT_MS)
         }
       }
     }
     window.addEventListener('jarvis-tool-call', handleTool)
-    return () => window.removeEventListener('jarvis-tool-call', handleTool)
+    return () => {
+      window.removeEventListener('jarvis-tool-call', handleTool)
+      if (toolTimerRef.current) {
+        clearTimeout(toolTimerRef.current)
+      }
+    }
   }, [])
```

---

### File 5: `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`

```diff
--- a/src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
+++ b/src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
@@ -163,7 +163,7 @@ describe('Empirical Verification: Holographic Core Lifecycle & State Machine', ()
       for (const { tool, expected } of validCases) {
         const props: SphereProps = {
           activeTool: tool,
-          isSpeaking: true, // Level 4 should be overridden by Level 3
+          isSpeaking: false,
           isThinking: true,
           isListening: true,
         }
@@ -171,6 +171,9 @@ describe('Empirical Verification: Holographic Core Lifecycle & State Machine', ()
       }
 
+      // M2 Canonical Hierarchy verification: SPEAKING (80) takes precedence over ACTIVE_TOOL (70)
+      expect(resolveActiveState({ activeTool: 'shell_command', isSpeaking: true })).toBe('SPEAKING')
+
       // Whitespace / empty activeTool falls through to Level 4
       expect(resolveActiveState({ activeTool: '   ', isSpeaking: true })).toBe('SPEAKING')
       expect(resolveActiveState({ activeTool: '', isThinking: true })).toBe('THINKING')
```

---

## 4. Verification and Validation Protocol

Once the Worker applies these changes, the following four verification steps must be executed:

1. **Adversarial Stress Test Verification**:
   ```powershell
   npx tsx tests/test_challenger_m2_adversarial_stress.ts
   ```
   **Pass Requirement**: Total Probes Executed: 29, Passed: 29, Failed: 0, Confirmed Vulnerabilities: 0. Verdict: `APPROVE`.

2. **Holographic Core Vitest Verification**:
   ```powershell
   npx vitest run src/components/dashboard/holographic-core
   ```
   **Pass Requirement**: All 3 test files (`event-wiring.test.ts`, `adversarial-m2.test.ts`, `empirical-lifecycle.test.ts`) must pass 66/66 tests.

3. **TypeScript Typecheck Verification**:
   ```powershell
   npm run typecheck
   ```
   **Pass Requirement**: 0 errors across `tsconfig.json`, `tsconfig.electron.json`, and `tsconfig.e2e.json`.

4. **Production Build Verification**:
   ```powershell
   npx vite build
   ```
   **Pass Requirement**: Production bundle builds with 0 errors.
