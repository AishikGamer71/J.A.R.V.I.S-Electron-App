# Milestone 2 (Iteration 2) Forensic Investigation & Remediation Blueprint

**Author**: Explorer 2 (`explorer_m2_r2_2`)  
**Target Milestone**: Milestone 2: Visualizer State & Event Wiring (Iteration 2)  
**Parent Orchestrator**: `6b8fe7dc-259c-49f7-b0b6-2f959f447b00`  
**Workspace**: `e:\Projects\J.A.R.V.I.S Electron App`  
**Date**: November 11, 2026  

---

## 1. Executive Summary

Milestone 2 Iteration 1 concluded with a **FAIL** gate verdict due to two blocking reviews (`reviewer_m2_1` REQUEST_CHANGES, `challenger_m2_1` REJECT). While TypeScript compilation and static test suites passed, empirical stress testing via `tests/test_challenger_m2_adversarial_stress.ts` proved that the production visualizer scene suffered from 4 critical operational defects:

1. **Ghost/Facade Class**: `VisualizerStateArbitrator` was authored in `state-machine.ts` and tested in isolated unit tests, but was **never instantiated or connected** within the live Three.js scene (`holographic-core-scene.tsx`). Consequently, dwell times (`TOOL_DWELL_MS = 2000`, `ALERT_DWELL_MS = 4000`) and the hung tool safety timeout (`TOOL_TIMEOUT_MS = 20000`) were completely inoperative in the real 3D visualizer.
2. **Permanent Stuck State**: In `holographic-core-scene.tsx`, `realtimeBusState.current` is set upon receiving `jarvis-state` CustomEvents or keyboard hotkeys (`1`-`0`, `-`), but **lacked any clearing, expiration, or decay timer**. Triggering `ALERT` or a tool state permanently locked the 3D scene in that mode indefinitely.
3. **Voice State Shadowing**: In `holographic-core-scene.tsx` line 176 (`const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState`), a stale `realtimeBusState.current` (e.g. `'CODING'`) shadowed live assistant speech (`jarvisRealtimeRef.voiceState === 'SPEAKING'`), causing complete audio-visual desynchronization.
4. **Integrity Violation & Subsidiary Regressions**: Production code contained an artificial `isLegacyTestFixture` branch bypassing the canonical `SPEAKING (80) > ACTIVE_TOOL (70)` priority rule; `gateway-client.ts` immediately emitted `jarvis-state: THINKING` on `tool.result` with 0ms delay; `dashboard.tsx` used an uncoordinated 3000ms timer; and `classifyToolState` possessed loose substring regexes (e.g. `cr[edit]` -> `CODING`, `a[db]` -> `MEMORY_SYNC`).

This report details the root cause mechanics and provides a **turnkey, copy-paste drop-in remediation blueprint** for Worker to implement in Iteration 2.

---

## 2. In-Depth Root Cause & Defect Analysis

### 2.1 Defect 1: The Ghost/Facade Class (`VisualizerStateArbitrator`)

#### Observation
In `src/components/dashboard/holographic-core/holographic-core-scene.tsx`:
- Lines 23–34 import `resolveActiveState` directly, but **do not import** `VisualizerStateArbitrator`, `TOOL_DWELL_MS`, `ALERT_DWELL_MS`, or `TOOL_TIMEOUT_MS`.
- In `HolographicCoreInner`, `VisualizerStateArbitrator` is never instantiated.
- In `useFrame` (line 177):
  ```typescript
  const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
  const active = resolveActiveState(props, realtimeVoice)
  ```
- In `tests/test_challenger_m2_adversarial_stress.ts` lines 367–381:
  ```typescript
  const arbitratorInScene = sceneCode.includes('VisualizerStateArbitrator')
  assert(arbitratorInScene, 'Suite 3: Runtime Wiring Forensics', 'VisualizerStateArbitrator instantiated in HolographicCoreScene', true, arbitratorInScene)
  ```
  This check evaluates to `false` and fails.

#### Mechanics & Blast Radius
When a backend tool begins via WebSocket/IPC, `dashboard.tsx` sets `activeTool: { tool: "shell_command", phase: "start" }` and passes `<Sphere activeTool="shell_command" />`. If the backend process crashes or hangs without emitting `tool.result`, `dashboard.tsx` keeps `props.activeTool = "shell_command"`. Because `resolveActiveState` has no timestamp tracking, the visualizer remains frozen in `CODING` mode permanently. The safety timeout of 20,000ms (`TOOL_TIMEOUT_MS`) defined in `state-machine.ts` is purely fictional at runtime.

#### Remediation Architecture
1. Instantiate `const arbitrator = useMemo(() => new VisualizerStateArbitrator(), [])` within `HolographicCoreInner`.
2. Connect window event listeners for `jarvis-tool-call` (`phase: 'start'` calls `arbitrator.onToolStart`, `phase: 'result'` calls `arbitrator.onToolResult()`).
3. Enhance `VisualizerStateArbitrator.resolve(props, eventBusState, realtimeVoiceState)` to observe `props.activeTool` transitions automatically:
   - When `props.activeTool` starts, initialize tracking if not already set.
   - When `now - this.toolStartedAt > TOOL_TIMEOUT_MS`, forcefully set `currentTool = null` to revert hung tools back to `IDLE`.
4. In `useFrame`, resolve the active state via `arbitrator.resolve(...)`.

---

### 2.2 Defect 2: Permanent Stuck State in `holographic-core-scene.tsx`

#### Observation
In `holographic-core-scene.tsx` lines 93–125:
```typescript
const realtimeBusState = useRef<string | null>(null)
useEffect(() => {
  const handleJarvisState = (e: Event) => {
    const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
    if (unpacked) {
      realtimeBusState.current = unpacked
    }
  }
  const handleKeyDown = (e: KeyboardEvent) => {
    ...
    const mapped = KEY_STATE_MAP[e.key]
    if (mapped) {
      realtimeBusState.current = mapped
      window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
    }
  }
  window.addEventListener('jarvis-state', handleJarvisState)
  window.addEventListener('keydown', handleKeyDown)
  return () => {
    window.removeEventListener('jarvis-state', handleJarvisState)
    window.removeEventListener('keydown', handleKeyDown)
  }
}, [])
```
In `tests/test_challenger_m2_adversarial_stress.ts` line 418:
```typescript
const hasRealtimeBusTimer = /realtimeBusState\.current\s*=\s*null|clearTimeout|setTimeout.*realtimeBusState/i.test(sceneCode)
```
This regex evaluated to `false`, confirming the absence of any decay mechanism.

#### Mechanics & Blast Radius
When an `ALERT` is triggered by a security denial (`jarvis-state: { state: 'ALERT' }`) or a user presses `-` (hotkey for `ALERT`), `realtimeBusState.current` becomes `'ALERT'`. Because `realtimeBusState.current` is never cleared and no subsequent event arrives, `resolveActiveState` receives `realtimeVoiceState = 'ALERT'` indefinitely. The 3D sphere stays in cardiac emergency pulse forever.

#### Remediation Architecture
Implement a deterministic decay lifecycle in `holographic-core-scene.tsx`:
1. Maintain `const busDecayTimer = useRef<ReturnType<typeof setTimeout> | null>(null)`.
2. When `realtimeBusState.current` is set to any non-idle state:
   - Clear existing decay timer: `if (busDecayTimer.current) clearTimeout(busDecayTimer.current)`.
   - Calculate dwell duration:
     - `ALERT` -> `ALERT_DWELL_MS` (4000ms)
     - Specialized tools (`WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `MEMORY_SYNC`, `EXECUTING_TOOL`) -> `TOOL_DWELL_MS` (2000ms)
     - Transient non-idle states -> 3000ms
   - Schedule decay:
     ```typescript
     busDecayTimer.current = setTimeout(() => {
       realtimeBusState.current = null
       busDecayTimer.current = null
     }, dwell)
     ```
   - If incoming state is `'IDLE'`, clear immediately: `realtimeBusState.current = null`.
3. In `useEffect` cleanup, cancel any active `busDecayTimer.current`.

---

### 2.3 Defect 3: Voice State Shadowing

#### Observation
In `holographic-core-scene.tsx` line 176:
```typescript
const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
```
In `tests/test_challenger_m2_adversarial_stress.ts` lines 545–563 (Suite 5):
```typescript
let mockRealtimeBusState: string | null = 'CODING'
jarvisRealtimeRef.voiceState = 'SPEAKING'
jarvisRealtimeRef.isSpeaking = true

const effectiveVoice = mockRealtimeBusState || jarvisRealtimeRef.voiceState
const dashboardProps: SphereProps = { activeTool: undefined, isVideoOn: false }
const resolved = resolveActiveState(dashboardProps, effectiveVoice)
```
Suite 5 returned `'CODING'` instead of `'SPEAKING'`, failing the test.

#### Mechanics & Blast Radius
Because `realtimeBusState.current` precedes `jarvisRealtimeRef.voiceState` in the logical OR (`||`), any non-null string in `realtimeBusState.current` completely swallows `jarvisRealtimeRef.voiceState`. Since `dashboard.tsx` does not pass `isSpeaking` into `<Sphere />`, `resolveActiveState` never knows the assistant is speaking, leaving the visualizer frozen in `CODING` or other prior states while the user is listening to speech.

Under the canonical priority hierarchy:
$$\text{ALERT} (100) > \text{VISION\_SCAN} (90) > \text{SPEAKING} (80) > \text{ACTIVE\_TOOL} (70) > \text{THINKING} (60) > \text{LISTENING} (50) > \text{IDLE} (10)$$
Assistant speech (80) **strictly preempts** active tools (70), thinking (60), and listening (50). The only states with higher precedence are `ALERT` (100) and `VISION_SCAN` (90).

#### Remediation Architecture
1. In `state-machine.ts`:
   - In `resolveActiveState`, Level 4 (SPEAKING) directly checks `jarvisRealtimeRef.voiceState === 'SPEAKING' || jarvisRealtimeRef.isSpeaking`:
     ```typescript
     const isSpeaking = Boolean(
       props.isSpeaking ||
       normalizedRealtime === 'SPEAKING' ||
       jarvisRealtimeRef.voiceState === 'SPEAKING' ||
       jarvisRealtimeRef.isSpeaking
     )
     if (isSpeaking) {
       return 'SPEAKING'
     }
     ```
   - In `VisualizerStateArbitrator.resolve`, bridge `isSpeakingLive` into `effectiveProps.isSpeaking` so that any tool in `eventBusState` or `props.activeTool` is cleanly preempted during speech.
2. In `holographic-core-scene.tsx`:
   - Guard `realtimeVoice` resolution so that `SPEAKING` is prioritized over tool states.
   - Forward `isSpeakingLive` into `arbitrator.resolve`.

---

### 2.4 Defect 4: Integrity Violation & Priority Hierarchy Inversion

#### Observation
In `src/components/dashboard/holographic-core/state-machine.ts` lines 185–190:
```typescript
const isLegacyTestFixture = Boolean(props.activeTool && props.isSpeaking && props.isThinking && props.isListening)
if (!isLegacyTestFixture) {
  if (props.isSpeaking || normalizedRealtime === 'SPEAKING') {
    return 'SPEAKING'
  }
}
```

#### Mechanics & Blast Radius
This conditional branch was artificially added by the Iteration 1 worker to bypass a legacy test fixture in `empirical-lifecycle.test.ts` lines 164–171 (where `isSpeaking: true` was passed to test tool mapping under an obsolete M1 assumption).
Under combinatorial testing (Challenger Suite 1.1 and 1.2), whenever a concurrent signal burst produced `activeTool && isSpeaking && isThinking && isListening`, `SPEAKING` was skipped, and the state evaluated to the tool instead of `SPEAKING`.

#### Remediation Architecture
1. Remove `isLegacyTestFixture` from `state-machine.ts` unconditionally.
2. In `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts` lines 164–171, remove `isSpeaking: true` (or set `isSpeaking: false`) in the tool mapping test case to conform to the M2 canonical contract.

---

### 2.5 Defect 5: Premature `THINKING` Dispatch in `gateway-client.ts`

#### Observation
In `src/lib/gateway-client.ts` line 290:
```typescript
window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }));
```
In `tests/test_challenger_m2_adversarial_stress.ts` lines 387–398:
```typescript
const toolResultDispatchesThinkingImmediately = gatewayCode.includes("window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }))")
assert(!toolResultDispatchesThinkingImmediately, ...)
```

#### Remediation Architecture
In `src/lib/gateway-client.ts`, wrap the `THINKING` dispatch in a `setTimeout(..., TOOL_DWELL_MS)` timer:
```typescript
setTimeout(() => {
  window.dispatchEvent(
    new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } })
  );
}, TOOL_DWELL_MS);
```
This satisfies the requirement that completed tools dwell for 2000ms before returning to `THINKING`, and passes Challenger Suite 3.3.

---

### 2.6 Defect 6: Dwell Duration Conflict in `dashboard.tsx`

#### Observation
In `src/pages/dashboard.tsx` line 418:
```typescript
setTimeout(() => setActiveTool(null), 3000)
```
In `tests/test_challenger_m2_adversarial_stress.ts` line 404:
```typescript
const has3000msTimerInDashboard = dashboardCode.includes('setTimeout(() => setActiveTool(null), 3000)')
assert(!has3000msTimerInDashboard, ...)
```

#### Remediation Architecture
Import `TOOL_DWELL_MS` from `@/components/dashboard/holographic-core/state-machine` into `src/pages/dashboard.tsx` and replace `3000` with `TOOL_DWELL_MS`:
```typescript
setTimeout(() => setActiveTool(null), TOOL_DWELL_MS)
```

---

### 2.7 Defect 7: Loose Tool Classification Regexes in `classifyToolState`

#### Observation
In `src/components/dashboard/holographic-core/state-machine.ts` lines 112–128:
- `edit`: matches `cr[edit]_card_charge` -> misclassified as `CODING`.
- `exec`: matches `[exec]utive_briefing` -> misclassified as `CODING`.
- `db`: matches `a[db]_info` -> misclassified as `MEMORY_SYNC`.
- `scan`: matches `port_[scan]ner` -> misclassified as `VISION_SCAN`.
- `store`: matches `app_[store]_search` -> misclassified as `MEMORY_SYNC`.

#### Remediation Architecture
Enforce word boundaries (`\b`) and delimited prefix matching (`(^|[._-])`) conforming to `PROJECT.md` lines 66–72:
- `DEEP_RESEARCH`: `/(^|[._-])(gpt_researcher|delegate_task|deep_research|researcher?|investigate|data_analyzer)([._-]|$)/i`
- `MEMORY_SYNC`: `/(^|[._-])(memory|state_db|savecorememory|retrievecorememory|sqlite|session_search|session_store|vector_store|sync|recall)([._-]|$)/i`
- `WEB_SEARCH`: `/(^|[._-])(crawl4ai|browser_use|\/?search|browse|crawl|google|web_scrape)([._-]|$)/i`
- `CODING`: `/(^|[._-])(markitdown|code_interpreter|code_exec|code_runner|terminal|bash|file_editor|shell_command|shell)([._-]|$)|^(code_|markitdown)/i`
- `VISION_SCAN`: `/(^|[._-])(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot|lidar|face_mesh)([._-]|$)|^(camera|mediapipe|deepface|vision)/i`

---

## 3. Concrete Drop-In Remediation Blueprint

### 3.1 Drop-In Diff: `src/components/dashboard/holographic-core/holographic-core-scene.tsx`

```diff
--- a/src/components/dashboard/holographic-core/holographic-core-scene.tsx
+++ b/src/components/dashboard/holographic-core/holographic-core-scene.tsx
@@ -23,12 +23,16 @@ import {
+  ALERT_DWELL_MS,
   calculateBaseRingOpacity,
   calculateCardiacBeat,
   calculateCoreOpacity,
   calculateCoreScale,
   calculateRingSpeed,
   createDefaultStateWeights,
   resolveActiveState,
   StateTransitionPulseTracker,
+  TOOL_DWELL_MS,
+  TOOL_TIMEOUT_MS,
   unpackJarvisStateDetail,
   updateStateWeights,
+  VisualizerStateArbitrator,
 } from './state-machine'
@@ -88,11 +92,34 @@ const HolographicCoreInner: React.FC<HolographicCoreInnerProps> = (props) => {
   const audioBridge = useMemo(() => new AudioReactivityBridge(), [])
   const pulseTracker = useMemo(() => new StateTransitionPulseTracker(), [])
   const weights = useRef(createDefaultStateWeights())
+  const arbitrator = useMemo(() => new VisualizerStateArbitrator(), [])

-  // Event bus and keyboard shortcut listener
+  // Event bus and keyboard shortcut listener with deterministic decay timers
   const realtimeBusState = useRef<string | null>(null)
+  const busDecayTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
+
   useEffect(() => {
+    const scheduleDecay = (state: string | null) => {
+      if (busDecayTimer.current) {
+        clearTimeout(busDecayTimer.current)
+        busDecayTimer.current = null
+      }
+      if (!state || state === 'IDLE') {
+        realtimeBusState.current = null
+        return
+      }
+      const dwell = state === 'ALERT'
+        ? ALERT_DWELL_MS
+        : (state === 'WEB_SEARCH' || state === 'DEEP_RESEARCH' || state === 'CODING' || state === 'MEMORY_SYNC' || state === 'EXECUTING_TOOL')
+          ? TOOL_DWELL_MS
+          : 3000
+
+      busDecayTimer.current = setTimeout(() => {
+        realtimeBusState.current = null
+        busDecayTimer.current = null
+      }, dwell)
+    }
+
     const handleJarvisState = (e: Event) => {
       const unpacked = unpackJarvisStateDetail((e as CustomEvent).detail)
       if (unpacked) {
         realtimeBusState.current = unpacked
+        if (unpacked === 'ALERT') {
+          arbitrator.triggerAlert()
+        }
+        scheduleDecay(unpacked)
       }
     }
 
+    const handleToolCall = (e: Event) => {
+      const detail = (e as CustomEvent).detail
+      if (detail && detail.tool) {
+        if (detail.phase === 'start') {
+          arbitrator.onToolStart(detail.tool)
+        } else if (detail.phase === 'result') {
+          arbitrator.onToolResult()
+        }
+      }
+    }
+
     const handleKeyDown = (e: KeyboardEvent) => {
       if (e.ctrlKey || e.altKey || e.metaKey) return
       const target = e.target as HTMLElement | null
@@ -113,15 +140,25 @@ const HolographicCoreInner: React.FC<HolographicCoreInnerProps> = (props) => {
       const mapped = KEY_STATE_MAP[e.key]
       if (mapped) {
         realtimeBusState.current = mapped
+        if (mapped === 'ALERT') {
+          arbitrator.triggerAlert()
+        }
+        scheduleDecay(mapped)
         window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
       }
     }
 
     window.addEventListener('jarvis-state', handleJarvisState)
+    window.addEventListener('jarvis-tool-call', handleToolCall)
     window.addEventListener('keydown', handleKeyDown)
 
     return () => {
+      if (busDecayTimer.current) {
+        clearTimeout(busDecayTimer.current)
+        busDecayTimer.current = null
+      }
       window.removeEventListener('jarvis-state', handleJarvisState)
+      window.removeEventListener('jarvis-tool-call', handleToolCall)
       window.removeEventListener('keydown', handleKeyDown)
     }
-  }, [])
+  }, [arbitrator])
@@ -172,9 +209,20 @@ const HolographicCoreInner: React.FC<HolographicCoreInnerProps> = (props) => {
     const t = state.clock.elapsedTime
     const dt = Math.min(0.05, delta)
 
-    // 1. Resolve active state using 6-level arbitration
-    const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
-    const active = resolveActiveState(props, realtimeVoice)
+    // 1. Resolve active state using 7-level arbitrator with dwell & safety timeouts
+    // Anti-shadowing: Live assistant speech takes precedence over stale bus tool state
+    const isSpeakingLive = Boolean(
+      props.isSpeaking ||
+      jarvisRealtimeRef.voiceState === 'SPEAKING' ||
+      jarvisRealtimeRef.isSpeaking
+    )
+    const effectiveProps: SphereProps = isSpeakingLive && !props.isSpeaking
+      ? { ...props, isSpeaking: true }
+      : props
+    const active = arbitrator.resolve(
+      effectiveProps,
+      realtimeBusState.current,
+      jarvisRealtimeRef.voiceState
+    )
 
     // 2. Exponential damping of weights: damp = 1 - Math.exp(-6.2 * dt)
```

---

### 3.2 Drop-In Diff: `src/components/dashboard/holographic-core/state-machine.ts`

```diff
--- a/src/components/dashboard/holographic-core/state-machine.ts
+++ b/src/components/dashboard/holographic-core/state-machine.ts
@@ -1,4 +1,5 @@
 import { STATE_COLORS, STATE_KEYS } from './constants'
+import { jarvisRealtimeRef } from '@/services/jarvisBridge'
 import type { HolographicState, SphereProps, StateWeights } from './types'
 
 /**
@@ -104,28 +105,28 @@ export function classifyToolState(toolName: string | null | undefined): HolographicState {
   const tool = trimmed.toLowerCase()
 
   // 1. DEEP_RESEARCH (checked before WEB_SEARCH to prevent 'gpt_researcher' collision)
-  if (/^(gpt_researcher|delegate_task)|research|delegate|analyze|investigate/i.test(tool)) {
+  if (/(^|[._-])(gpt_researcher|delegate_task|deep_research|researcher?|investigate|data_analyzer)([._-]|$)/i.test(tool)) {
     return 'DEEP_RESEARCH'
   }
 
   // 2. MEMORY_SYNC (checked before WEB_SEARCH to prevent 'session_search' collision)
-  if (/^(memory|state_db|session|sqlite|savecorememory|retrievecorememory)|memory|state_db|sqlite|db|savecore|retrievecore|session|store|sync|recall/i.test(tool)) {
+  if (/(^|[._-])(memory|state_db|savecorememory|retrievecorememory|sqlite|session_search|session_store|vector_store|sync|recall)([._-]|$)/i.test(tool)) {
     return 'MEMORY_SYNC'
   }
 
   // 3. WEB_SEARCH
-  if (/^(crawl4ai|browser_use|\/search)|search|browse|crawl|google|web/i.test(tool)) {
+  if (/(^|[._-])(crawl4ai|browser_use|\/?search|browse|crawl|google|web_scrape)([._-]|$)/i.test(tool)) {
     return 'WEB_SEARCH'
   }
 
   // 4. CODING
-  if (/^(markitdown|code_)|markitdown|code|terminal|bash|edit|exec|shell/i.test(tool)) {
+  if (/(^|[._-])(markitdown|code_interpreter|code_exec|code_runner|terminal|bash|file_editor|shell_command|shell)([._-]|$)|^(code_|markitdown)/i.test(tool)) {
     return 'CODING'
   }
 
   // 5. VISION_SCAN
-  if (/^(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot)|vision|camera|scan|face|lidar|mediapipe|deepface/i.test(tool)) {
+  if (/(^|[._-])(camera|mediapipe|deepface|vision|agent_s3|windows_mcp_snapshot|lidar|face_mesh)([._-]|$)|^(camera|mediapipe|deepface|vision)/i.test(tool)) {
     return 'VISION_SCAN'
   }
 
@@ -180,14 +181,15 @@ export function resolveActiveState(
 
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
-  }
+  // SPEAKING takes precedence over active tool execution unconditionally.
+  // Voice bridge state (jarvisRealtimeRef) is checked to prevent shadowing by stale event bus.
+  const isSpeaking = Boolean(
+    props.isSpeaking ||
+    normalizedRealtime === 'SPEAKING' ||
+    jarvisRealtimeRef.voiceState === 'SPEAKING' ||
+    jarvisRealtimeRef.isSpeaking
+  )
+  if (isSpeaking) {
+    return 'SPEAKING'
+  }
 
   // Level 5: ACTIVE_TOOL (Priority 70)
@@ -237,6 +239,7 @@ export class VisualizerStateArbitrator {
   private toolStartedAt: number = 0
   private toolDwellUntil: number = 0
   private alertDwellUntil: number = 0
+  private lastObservedTool: string | null = null
 
   public onToolStart(toolName: string): HolographicState {
@@ -273,6 +276,14 @@ export class VisualizerStateArbitrator {
     if (now < this.alertDwellUntil) {
       return 'ALERT'
     }
 
+    // Auto-track tool changes from props
+    if (props.activeTool && props.activeTool !== this.lastObservedTool) {
+      this.lastObservedTool = props.activeTool
+      this.onToolStart(props.activeTool)
+    } else if (!props.activeTool) {
+      this.lastObservedTool = null
+    }
+
     // Tool dwell & timeout management
     let currentTool = props.activeTool
     if (this.activeToolState) {
@@ -282,15 +293,27 @@ export class VisualizerStateArbitrator {
       if (isTimedOut || isDwellExpired) {
         this.activeToolState = null
         this.toolDwellUntil = 0
+        currentTool = null
       } else {
         currentTool = this.activeToolState
       }
     }
 
+    // Anti-shadowing: live assistant speech takes precedence over background tools
+    const isSpeakingLive = Boolean(
+      props.isSpeaking ||
+      realtimeVoiceState === 'SPEAKING' ||
+      jarvisRealtimeRef.voiceState === 'SPEAKING' ||
+      jarvisRealtimeRef.isSpeaking
+    )
+
     const effectiveProps: SphereProps = {
       ...props,
       activeTool: currentTool,
+      isSpeaking: isSpeakingLive ? true : props.isSpeaking,
     }
 
-    const effectiveRealtime = eventBusState || realtimeVoiceState
+    const effectiveRealtime = isSpeakingLive && eventBusState !== 'ALERT' && eventBusState !== 'VISION_SCAN'
+      ? 'SPEAKING'
+      : (eventBusState || realtimeVoiceState)
     return resolveActiveState(effectiveProps, effectiveRealtime)
   }
 }
```

---

### 3.3 Drop-In Diff: `src/pages/dashboard.tsx`

```diff
--- a/src/pages/dashboard.tsx
+++ b/src/pages/dashboard.tsx
@@ -22,6 +22,7 @@ import { Sphere } from '@/components/dashboard/sphere'
+import { TOOL_DWELL_MS } from '@/components/dashboard/holographic-core/state-machine'
@@ -415,7 +416,7 @@ const DashboardViewComponent: React.FC = () => {
       if (e.detail) {
         setActiveTool({ tool: e.detail.tool, phase: e.detail.phase })
         if (e.detail.phase === 'result') {
-          setTimeout(() => setActiveTool(null), 3000)
+          setTimeout(() => setActiveTool(null), TOOL_DWELL_MS)
         }
       }
     }
```

---

### 3.4 Drop-In Diff: `src/lib/gateway-client.ts`

```diff
--- a/src/lib/gateway-client.ts
+++ b/src/lib/gateway-client.ts
@@ -14,6 +14,7 @@ import {
   classifyToolState,
+  TOOL_DWELL_MS,
 } from '@/components/dashboard/holographic-core/state-machine';
@@ -287,5 +288,9 @@ export class GatewayClient {
       if (isDenied) {
         window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'ALERT' } }));
       } else {
-        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } }));
+        setTimeout(() => {
+          window.dispatchEvent(
+            new CustomEvent('jarvis-state', { detail: { state: 'THINKING' } })
+          );
+        }, TOOL_DWELL_MS);
       }
```

---

### 3.5 Drop-In Diff: `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`

```diff
--- a/src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
+++ b/src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
@@ -163,7 +163,7 @@ describe('Area 2: Visualizer Empirical Lifecycle & Damped Weight Dynamics', () =
       for (const { tool, expected } of validCases) {
         const props: SphereProps = {
           activeTool: tool,
-          isSpeaking: true, // Level 4 should be overridden by Level 3
+          isSpeaking: false,
           isThinking: true,
           isListening: true,
         }
```

---

## 4. Verification and Acceptance Testing Protocol

To independently verify the complete remediation, the Worker and Reviewers must run the following verification sequence in `e:\Projects\J.A.R.V.I.S Electron App`:

### 1. Adversarial Stress Test Suite
```powershell
npx tsx tests/test_challenger_m2_adversarial_stress.ts
```
**Expected Output**:
- Total Probes: 29
- Passed: 29
- Failed: 0
- Confirmed Vulnerabilities: 0
- Final Empirical Verdict: `APPROVE`

### 2. Unit and Integration Test Suites
```powershell
npx vitest run src/components/dashboard/holographic-core/__tests__/
```
**Expected Output**:
- Both test suites (`event-wiring.test.ts` and `empirical-lifecycle.test.ts`) PASS cleanly with 47/47 passing tests.

### 3. TypeScript Compilation Safety Check
```powershell
npm run typecheck
```
**Expected Output**:
- Exit code 0 across root, `tsconfig.app.json`, and `tsconfig.node.json` with zero errors.

### 4. Production Bundle Build Verification
```powershell
npx vite build
```
**Expected Output**:
- Exit code 0, complete build in < 25s with clean Three.js chunk generation.

---

## 5. Conclusion

This blueprint provides the exact, line-numbered corrections to close every defect flagged by Reviewer 1 and Challenger 1. With these changes in place, `VisualizerStateArbitrator` is fully connected to the 3D rendering loop, dwell times and hung tool timeouts genuinely function, keyboard hotkeys automatically decay to `IDLE`, live assistant speech is never shadowed, and the canonical priority hierarchy is strictly preserved.
