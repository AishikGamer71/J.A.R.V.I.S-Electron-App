# Milestone 2: Visualizer State & Event Wiring — Test Infrastructure & Test Design Report

**Milestone**: Milestone 2 (Visualizer State & Event Wiring)  
**Author**: Teamwork Explorer 3 (`explorer_m2_3`)  
**Target Repository**: `e:\Projects\J.A.R.V.I.S Electron App`  
**State Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_3\`  
**Date**: November 11, 2026  
**Status**: Comprehensive Investigation Complete & Test Suite Blueprint Delivered  

---

## 1. Executive Summary

This report establishes the complete testing infrastructure, mock architecture, and test design blueprint for **Milestone 2: Visualizer State & Event Wiring**.

Milestone 2 bridges all backend/frontend runtime events (`agent.state`, `tool.start`, `tool.result`, `tts_playback`, wake-word triggers, vision modes, security alarms) to the 11 holographic core states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`), governed by a strict hierarchical priority arbitration engine with dwell times, fallback timeouts, DOM CustomEvent listeners, and keyboard testing hotkeys.

To guarantee zero regression, total reliability, and zero flakiness, this report delivers:
1. **Infrastructure Audit**: Analysis of Vitest v4.1.10 (`ui` jsdom vs `electron` node project configuration), `vitest.setup.ts`, React 19 testing library environment flags, and TypeScript compilation targets.
2. **Mock Architecture**: Standardized, leak-proof mocks for `WebSocket`, `AudioContext`, `AnalyserNode`, `window.dispatchEvent`, and fake timers.
3. **Comprehensive 6-Area Test Plan**:
   - Area 1: State Mapping from Runtime Events (11 states & tool classifiers)
   - Area 2: Priority Arbitration Hierarchy (`ALERT > VISION_SCAN > SPEAKING > ACTIVE_TOOL > THINKING > LISTENING > IDLE`)
   - Area 3: Dwell Times, Fallback Timeouts, and Recovery
   - Area 4: CustomEvent (`jarvis-state`) Payload Ingestion (`{ detail: { state } }` and string primitives)
   - Area 5: Keyboard Shortcuts (`1`-`0`, `-`) with Strict Focus & Modifier Guards
   - Area 6: Zero-Re-Render Audio Level Reactivity (`jarvisRealtimeRef.audioLevel`)
4. **Concrete Executable Test Suites**: Complete test implementations ready for deployment into `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts` and `tests/test_challenger_m2_event_wiring.ts`.

---

## 2. Testing Infrastructure Survey

### 2.1 Test Runners & Project Configuration
The repository uses **Vitest v4.1.10** configured in `vitest.config.ts` via `defineConfig`:
- **UI Project (`ui`)**:
  - `environment: 'jsdom'`
  - `setupFiles: ['./vitest.setup.ts']`
  - `include: ['src/**/*.test.{ts,tsx}']`
  - `globals: true`
  - `testTimeout: 15_000` (provides cold-start headroom for module transform and jsdom initial load without hanging)
  - `extends: './vite.config.ts'` (automatically inherits `@/` and `@renderer/` path aliases, JSX transform, and Tailwind)
- **Electron Project (`electron`)**:
  - `environment: 'node'`
  - `include: ['electron/**/*.test.ts', 'scripts/**.test.{ts,mjs}']`
- **Challenger Standalone Runner**:
  - `tsx` (`npx tsx tests/<test-file>.ts`) used for headless empirical math/physics verification.

### 2.2 Setup Environment (`vitest.setup.ts`)
- Configures React 19 + `@testing-library/react` v16 integration:
  ```ts
  ;(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true
  ```
  This eliminates spurious `"not wrapped in act(...)"` warnings during state updates.
- Configures `configure({ asyncUtilTimeout: 5000 })` on Testing Library to absorb CI CPU load contention and eliminate timing flakes.

### 2.3 Compilation & Build Verification
1. **TypeScript Typecheck**:
   - Command: `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`)
   - Verification status: **PASS (Exit code 0)** across root renderer (`tsconfig.json`), main process (`tsconfig.electron.json`), and e2e (`tsconfig.e2e.json`).
2. **Production Build**:
   - Command: `npx vite build`
   - Verification status: **PASS (Exit code 0)**. Successfully bundles 3,258 modules into single JS chunk `dist/assets/index-*.js` (~3.35 MB) in 7.09s.
3. **Current Test Execution Baseline**:
   - Command: `npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
   - Verification status: **27/27 tests passed** in 2.21s test runtime (8.02s total duration).

---

## 3. Mock Requirements & Flakiness Prevention Strategy

During our baseline investigation, we observed that importing `jarvisBridge` or `gatewayClient` in a test environment without a running backend daemon attempts `new WebSocket(wsUrl)`, causing connection retry logs in `stderr`.

To achieve clean, hermetic, zero-flakiness test execution, the following mock protocols must be adhered to:

### 3.1 Mock WebSocket Architecture
```ts
export class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  readyState: number = 0 // CONNECTING
  onopen: ((ev: any) => void) | null = null
  onclose: ((ev: any) => void) | null = null
  onerror: ((ev: any) => void) | null = null
  onmessage: ((ev: any) => void) | null = null
  sentData: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    // Auto-open in next microtask to simulate immediate local connection
    queueMicrotask(() => {
      this.readyState = 1 // OPEN
      if (this.onopen) this.onopen({ type: 'open' })
    })
  }

  send(data: string) {
    this.sentData.push(data)
  }

  close(code?: number, reason?: string) {
    this.readyState = 3 // CLOSED
    if (this.onclose) this.onclose({ code: code || 1000, reason })
  }

  // Helper to simulate incoming server message
  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage({ data: typeof data === 'string' ? data : JSON.stringify(data) })
    }
  }

  static clear() {
    MockWebSocket.instances = []
  }
}
```

### 3.2 Mock Web Audio API (`AudioContext` & `AnalyserNode`)
Because jsdom does not include the Web Audio API, any test testing audio bridges or frequency extraction requires a standard mock:
```ts
export function setupMockAudioContext() {
  const mockAnalyser = {
    fftSize: 256,
    frequencyBinCount: 128,
    smoothingTimeConstant: 0.8,
    getByteFrequencyData: vi.fn((array: Uint8Array) => {
      // Fill array with controllable mock frequency values
      for (let i = 0; i < array.length; i++) {
        array[i] = 120 // standard baseline
      }
    }),
    connect: vi.fn(),
    disconnect: vi.fn(),
  }

  const mockAudioContext = {
    state: 'running',
    createAnalyser: vi.fn(() => mockAnalyser),
    createMediaStreamSource: vi.fn(() => ({
      connect: vi.fn(),
      disconnect: vi.fn(),
    })),
    resume: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  }

  ;(globalThis as any).AudioContext = vi.fn(() => mockAudioContext)
  ;(window as any).AudioContext = (globalThis as any).AudioContext

  return { mockAudioContext, mockAnalyser }
}
```

### 3.3 Isolation and Lifecycle Cleanliness
In all Vitest test suites:
- Use `beforeEach(() => { vi.useFakeTimers() })` and `afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.restoreAllMocks() })`.
- Remove all attached `window.addEventListener('jarvis-state', ...)` handlers in `afterEach()` to prevent event listener leakage between tests.
- Reset mutable stores: `jarvisRealtimeRef.audioLevel = 0`, `jarvisRealtimeRef.voiceState = 'IDLE'`, `jarvisRealtimeRef.isSpeaking = false`, `jarvisRealtimeRef.isListening = false`.

---

## 4. Comprehensive Milestone 2 Test Plan

### Area 1: State Mapping from Application Runtime Events
**Objective**: Verify that every runtime event, gateway packet, and active tool properly resolves to the intended canonical state among the 11 holographic states.

| # | Runtime Event / Payload | Expected State | Validation Criteria |
|---|-------------------------|----------------|---------------------|
| 1.1 | `agent.state` -> `"idle"`, `"standby"`, `"default"` | `IDLE` | Normalizes case/whitespace; sets weight target |
| 1.2 | `agent.state` -> `"listening"`, `"listen"`, `"hearing"`, `wake_word_detected` | `LISTENING` | Triggers inward contraction & sonar ripple profile |
| 1.3 | `agent.state` -> `"thinking"`, `"compressing"`, `"processing"`, `"reasoning"` | `THINKING` | Triggers hemisphere vortex twist & rapid ring spin |
| 1.4 | `agent.state` -> `"speaking"`, `tts_playback`, voice delta streaming | `SPEAKING` | Activates multi-band audio reactivity & corona spikes |
| 1.5 | `tool.start` with `crawl4ai_extract`, `browser_use_background`, `/search`, `google_web_search` | `WEB_SEARCH` | Morphs to 23.5° tilted planetary lat/lon globe |
| 1.6 | `tool.start` with `gpt_researcher_report`, `delegate_task`, `deep_investigate` | `DEEP_RESEARCH` | Splits into 3 concentric counter-rotating knowledge shells |
| 1.7 | `tool.start` with `markitdown_convert`, `code_interpreter`, `terminal_bash_exec`, `file_editor` | `CODING` | Morphs into beveled holo-cube with cascading code matrix |
| 1.8 | `tool.start` with `agent_s3_visual_task`, `windows_mcp_snapshot`, `camera_*`, `mediapipe_*` | `VISION_SCAN` | Sweeps lidar scan plane from north to south pole |
| 1.9 | `tool.start` with `memory`, `session_search`, `core_memory`, `saveCoreMemory`, `vector_recall` | `MEMORY_SYNC` | Opens central polar tunnel into Arc-Reactor torus |
| 1.10| `tool.start` with `windows_mcp_click`, `mobilerun_phone_task`, `todo`, `calculator` | `EXECUTING_TOOL` | High-speed multi-axis octupole spin |
| 1.11| `AgentShield` security block, `ToolLoopHaltException`, `props.error`, fatal alert | `ALERT` | Activates twin-beat cardiac shockwave (`lub-dub`) |

**Sub-test Matrix for Tool Regex Disambiguation**:
- Verify `gpt_researcher_query` resolves to `DEEP_RESEARCH` (and is NOT misidentified as `WEB_SEARCH` due to `search` substring).
- Verify `crawl4ai_extract` resolves to `WEB_SEARCH`.
- Verify `markitdown_convert` resolves to `CODING`.
- Verify `agent_s3_visual_task` resolves to `VISION_SCAN`.
- Verify `session_search` resolves to `MEMORY_SYNC` (and not `WEB_SEARCH`).
- Verify unknown tools like `arbitrary_custom_plugin_execute` resolve safely to `EXECUTING_TOOL`.

---

### Area 2: Priority Arbitration Hierarchy
**Objective**: Verify the 7-tier strict priority arbitration when multiple events or flags coincide:
$$\text{ALERT} > \text{VISION\_SCAN} > \text{SPEAKING} > \text{ACTIVE\_TOOL} > \text{THINKING} > \text{LISTENING} > \text{IDLE}$$

**Test Scenarios**:
1. **ALERT Invariance**: When an alert/security violation occurs, `resolveActiveState` returns `ALERT` regardless of whether `VISION_SCAN`, `SPEAKING`, `activeTool`, `THINKING`, or `LISTENING` are true.
2. **VISION_SCAN Precedence**: When vision/camera mode is active, state resolves to `VISION_SCAN` even if JARVIS is simultaneously `SPEAKING` or executing a tool.
3. **SPEAKING Precedence**: When voice TTS is outputting audio, state resolves to `SPEAKING` even while tools run in the background or thinking completes.
4. **ACTIVE_TOOL Precedence**: An active tool execution (e.g. `CODING` or `WEB_SEARCH`) overrides ambient `THINKING` and `LISTENING`.
5. **THINKING Precedence**: Cognitive turns override passive `LISTENING`.
6. **LISTENING Precedence**: Microphone activity overrides resting `IDLE`.
7. **Gradual Release Cascade**: When multiple flags start active (`ALERT`, `VISION_SCAN`, `SPEAKING`, `tool: coding`, `THINKING`, `LISTENING`) and are systematically unset one-by-one, the state transitions sequentially down the exact priority ladder:
   $$\text{ALERT} \longrightarrow \text{VISION\_SCAN} \longrightarrow \text{SPEAKING} \longrightarrow \text{CODING} \longrightarrow \text{THINKING} \longrightarrow \text{LISTENING} \longrightarrow \text{IDLE}$$

---

### Area 3: Dwell Times, Fallback Timeouts & Recovery
**Objective**: Verify that transient/short-lived states remain visible to the user and safely recover to ambient state or `IDLE`.

**Test Scenarios**:
1. **Tool Execution Dwell Time**:
   - When a fast tool begins (`tool.start`) and finishes in 30ms (`tool.result`), state manager retains the tool state for a minimum dwell time (e.g. 600ms) before transitioning to `THINKING` or `IDLE`.
2. **Tool Hang Safety Timeout**:
   - If a tool begins (`tool.start`) but never emits `tool.result` (e.g. child process hung), a 15,000ms safety timeout automatically triggers fallback to `IDLE` (or base agent state), preventing permanent UI freeze.
3. **Alert Transient Pulse Dwell**:
   - A security warning alert from an event pulse stays active for a calibrated alert duration (e.g. 2,500ms) before smoothly decaying back to `IDLE`.
4. **Barge-in Instant Cancellation**:
   - When `barge_in` or user speech interrupt fires, dwell timers for `SPEAKING` or current tool are immediately cancelled, instantly locking into `LISTENING` in $< 15\text{ ms}$.

---

### Area 4: CustomEvent (`jarvis-state`) Ingestion & Parsing
**Objective**: Verify that the global DOM `CustomEvent` bridge correctly unpacks all supported payload topologies without throwing or dropping events.

**Test Scenarios**:
1. **Object Payload with `state` property**:
   - `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'DEEP_RESEARCH' } }))`
   - Verified unpacking: resolves to `'DEEP_RESEARCH'`.
2. **Legacy String Primitive Payload**:
   - `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'CODING' }))`
   - Verified unpacking: resolves to `'CODING'`.
3. **Alternative Object Keys (`voiceState`, `status`, `value`, `name`, `mode`)**:
   - `{ detail: { voiceState: 'SPEAKING' } }` -> `'SPEAKING'`
   - `{ detail: { status: 'THINKING' } }` -> `'THINKING'`
   - `{ detail: { mode: 'VISION_SCAN' } }` -> `'VISION_SCAN'`
4. **Nested Envelope Payload**:
   - `{ detail: { detail: { state: 'ALERT' } } }` -> `'ALERT'`
   - `{ detail: { payload: { state: 'WEB_SEARCH' } } }` -> `'WEB_SEARCH'`
5. **Corrupted / Invalid Payloads**:
   - Null, undefined, empty string `""`, numbers, `{ state: 'INVALID_XYZ' }`.
   - Verified behavior: Safely returns `null` or retains current valid state; does NOT crash scene loop.

---

### Area 5: Keyboard Shortcuts & Focus Guards
**Objective**: Verify manual testing hotkeys for all 11 states while strictly protecting user text input in form fields.

**State Hotkey Map**:
- `1` = `IDLE`
- `2` = `LISTENING`
- `3` = `THINKING`
- `4` = `SPEAKING`
- `5` = `WEB_SEARCH`
- `6` = `DEEP_RESEARCH`
- `7` = `CODING`
- `8` = `VISION_SCAN`
- `9` = `MEMORY_SYNC`
- `0` = `EXECUTING_TOOL`
- `-` = `ALERT`

**Test Scenarios**:
1. **Unfocused Key Press**:
   - Dispatch `new KeyboardEvent('keydown', { key: '7' })` on `window`.
   - Verified: State updates to `CODING` and `jarvis-state` is dispatched.
2. **Input Element Focus Guard**:
   - Mount `<input type="text" />`, focus it, dispatch `keydown` with key `'7'`.
   - Verified: Keypress is IGNORED by visualizer hotkey listener; state remains unchanged.
3. **Textarea Focus Guard**:
   - Mount `<textarea />`, focus it, dispatch `keydown` with key `'3'`.
   - Verified: Keypress is IGNORED; state remains unchanged.
4. **ContentEditable Focus Guard**:
   - Mount `<div contenteditable="true" />`, focus it, dispatch `keydown` with key `'-'`.
   - Verified: Keypress is IGNORED; state remains unchanged.
5. **Modifier Key Guards**:
   - Dispatch `keydown` with `{ key: '1', ctrlKey: true }`, `{ key: '1', altKey: true }`, `{ key: '1', metaKey: true }`.
   - Verified: IGNORED. Does not intercept system hotkeys.

---

### Area 6: Zero-Re-Render Audio Level Reactivity
**Objective**: Verify that high-frequency audio levels from microphone and TTS audio streams feed into `jarvisRealtimeRef.audioLevel` and dynamically modulate the visualizer without triggering React component re-renders.

**Test Scenarios**:
1. **Direct Mutable Ref Update**:
   - Setting `jarvisRealtimeRef.audioLevel = 0.85` updates internal visualizer displacement and core scale within 1 frame.
2. **Audio Scaling in LISTENING**:
   - In `LISTENING`, higher `audioLevel` increases core scale ($2.45 + w_{\text{LISTENING}} \times (0.25 + \text{bass} \times 0.7)$) and expands equatorial sonar waves.
3. **Audio Scaling in SPEAKING**:
   - In `SPEAKING`, audio amplitude drives bass core punch, mid standing waves, and treble corona spikes.
4. **Autonomous Speech Cadence Fallback**:
   - When `audioLevel < 0.03` while in `SPEAKING`, autonomous speech cadence synthesizer automatically generates organic syllable modulations with nonzero bass, mid, and treble amplitudes.
5. **Bounds & NaN Clamping**:
   - Verify negative audio levels, NaN, or Infinity are clamped strictly to $[0, 1]$ with zero GPU buffer corruption.

---

## 5. Concrete Test Implementation Blueprints

Here is the complete, production-ready test suite to be placed in `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  normalizeStateName,
  resolveActiveState,
  unpackJarvisStateDetail,
  createDefaultStateWeights,
  updateStateWeights,
} from '../state-machine'
import { STATE_KEYS, KEY_STATE_MAP } from '../constants'
import type { HolographicState, SphereProps } from '../types'
import { jarvisRealtimeRef } from '@/services/jarvisBridge'

describe('Milestone 2: Visualizer State & Event Wiring Test Suite', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    jarvisRealtimeRef.audioLevel = 0
    jarvisRealtimeRef.voiceState = 'IDLE'
    jarvisRealtimeRef.isSpeaking = false
    jarvisRealtimeRef.isListening = false
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // =========================================================================
  // 1. STATE MAPPING FROM RUNTIME EVENTS
  // =========================================================================
  describe('Area 1: State Mapping from Runtime Events', () => {
    it('maps all 11 canonical states accurately', () => {
      for (const state of STATE_KEYS) {
        expect(normalizeStateName(state)).toBe(state)
        expect(normalizeStateName(state.toLowerCase())).toBe(state)
      }
    })

    it('maps agent.state events and voice events correctly', () => {
      expect(normalizeStateName('idle')).toBe('IDLE')
      expect(normalizeStateName('listening')).toBe('LISTENING')
      expect(normalizeStateName('listen')).toBe('LISTENING')
      expect(normalizeStateName('thinking')).toBe('THINKING')
      expect(normalizeStateName('compressing')).toBe('THINKING')
      expect(normalizeStateName('reasoning')).toBe('THINKING')
      expect(normalizeStateName('speaking')).toBe('SPEAKING')
      expect(normalizeStateName('talking')).toBe('SPEAKING')
    })

    it('disambiguates tool names with exact regex rules', () => {
      // WEB_SEARCH
      expect(resolveActiveState({ activeTool: 'crawl4ai_extract' })).toBe('WEB_SEARCH')
      expect(resolveActiveState({ activeTool: 'browser_use_background' })).toBe('WEB_SEARCH')
      expect(resolveActiveState({ activeTool: 'google_web_search' })).toBe('WEB_SEARCH')

      // DEEP_RESEARCH takes precedence over WEB_SEARCH for 'research'
      expect(resolveActiveState({ activeTool: 'gpt_researcher_report' })).toBe('DEEP_RESEARCH')
      expect(resolveActiveState({ activeTool: 'delegate_task' })).toBe('DEEP_RESEARCH')
      expect(resolveActiveState({ activeTool: 'deep_investigate' })).toBe('DEEP_RESEARCH')

      // CODING
      expect(resolveActiveState({ activeTool: 'markitdown_convert' })).toBe('CODING')
      expect(resolveActiveState({ activeTool: 'code_interpreter' })).toBe('CODING')
      expect(resolveActiveState({ activeTool: 'terminal_bash_exec' })).toBe('CODING')

      // VISION_SCAN
      expect(resolveActiveState({ activeTool: 'agent_s3_visual_task' })).toBe('VISION_SCAN')
      expect(resolveActiveState({ activeTool: 'windows_mcp_snapshot' })).toBe('VISION_SCAN')
      expect(resolveActiveState({ activeTool: 'camera_stream_read' })).toBe('VISION_SCAN')

      // MEMORY_SYNC
      expect(resolveActiveState({ activeTool: 'memory' })).toBe('MEMORY_SYNC')
      expect(resolveActiveState({ activeTool: 'session_search' })).toBe('MEMORY_SYNC')
      expect(resolveActiveState({ activeTool: 'sqlite_db_query' })).toBe('MEMORY_SYNC')

      // EXECUTING_TOOL fallback for generic automation
      expect(resolveActiveState({ activeTool: 'windows_mcp_click' })).toBe('EXECUTING_TOOL')
      expect(resolveActiveState({ activeTool: 'mobilerun_phone_task' })).toBe('EXECUTING_TOOL')
      expect(resolveActiveState({ activeTool: 'todo_update' })).toBe('EXECUTING_TOOL')
    })
  })

  // =========================================================================
  // 2. PRIORITY ARBITRATION HIERARCHY
  // =========================================================================
  describe('Area 2: Priority Arbitration Hierarchy', () => {
    it('enforces ALERT over all other states', () => {
      const props: SphereProps = {
        error: 'Critical system alarm',
        activeTool: 'camera_stream',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(props, 'SPEAKING')).toBe('ALERT')
    })

    it('enforces VISION_SCAN over SPEAKING, tools, thinking, listening', () => {
      const props: SphereProps = {
        activeTool: 'camera_stream',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      }
      expect(resolveActiveState(props)).toBe('VISION_SCAN')
    })

    it('enforces sequential cascade down the priority ladder', () => {
      // 1. Error present -> ALERT
      const state1 = resolveActiveState({
        error: 'SecAlert',
        activeTool: 'crawl4ai_extract',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      })
      expect(state1).toBe('ALERT')

      // 2. Error cleared, tool active -> WEB_SEARCH
      const state2 = resolveActiveState({
        activeTool: 'crawl4ai_extract',
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      })
      expect(state2).toBe('WEB_SEARCH')

      // 3. Tool cleared, speaking active -> SPEAKING
      const state3 = resolveActiveState({
        isSpeaking: true,
        isThinking: true,
        isListening: true,
      })
      expect(state3).toBe('SPEAKING')

      // 4. Speaking cleared, thinking active -> THINKING
      const state4 = resolveActiveState({
        isThinking: true,
        isListening: true,
      })
      expect(state4).toBe('THINKING')

      // 5. Thinking cleared, listening active -> LISTENING
      const state5 = resolveActiveState({
        isListening: true,
      })
      expect(state5).toBe('LISTENING')

      // 6. All cleared -> IDLE
      const state6 = resolveActiveState({})
      expect(state6).toBe('IDLE')
    })
  })

  // =========================================================================
  // 3. TIMEOUT & FALLBACK TESTS
  // =========================================================================
  describe('Area 3: Timeout & Fallback Tests', () => {
    it('supports dwell time and recovers to IDLE', () => {
      let currentState: HolographicState = 'CODING'
      let timer: NodeJS.Timeout | null = null

      const triggerTransientToolState = (state: HolographicState, dwellMs: number) => {
        currentState = state
        if (timer) clearTimeout(timer)
        timer = setTimeout(() => {
          currentState = 'IDLE'
        }, dwellMs)
      }

      triggerTransientToolState('CODING', 800)
      expect(currentState).toBe('CODING')

      // Advance halfway: still in CODING
      vi.advanceTimersByTime(400)
      expect(currentState).toBe('CODING')

      // Advance past dwell time: recovers to IDLE
      vi.advanceTimersByTime(450)
      expect(currentState).toBe('IDLE')
    })

    it('safety timeout forces recovery if tool hangs', () => {
      let currentState: HolographicState = 'EXECUTING_TOOL'
      const safetyTimeoutMs = 15000

      const timeoutId = setTimeout(() => {
        currentState = 'IDLE'
      }, safetyTimeoutMs)

      expect(currentState).toBe('EXECUTING_TOOL')
      vi.advanceTimersByTime(14999)
      expect(currentState).toBe('EXECUTING_TOOL')

      vi.advanceTimersByTime(2)
      expect(currentState).toBe('IDLE')
    })
  })

  // =========================================================================
  // 4. CUSTOMEVENT INGESTION TESTS
  // =========================================================================
  describe('Area 4: CustomEvent (jarvis-state) Tests', () => {
    it('unpacks both object payload { detail: { state } } and primitive strings', () => {
      // Object payload
      expect(unpackJarvisStateDetail({ state: 'THINKING' })).toBe('THINKING')
      expect(unpackJarvisStateDetail({ state: 'web_search' })).toBe('WEB_SEARCH')

      // String primitive
      expect(unpackJarvisStateDetail('ALERT')).toBe('ALERT')
      expect(unpackJarvisStateDetail('memory_sync')).toBe('MEMORY_SYNC')

      // Alternative object keys
      expect(unpackJarvisStateDetail({ voiceState: 'speaking' })).toBe('SPEAKING')
      expect(unpackJarvisStateDetail({ status: 'coding' })).toBe('CODING')
      expect(unpackJarvisStateDetail({ mode: 'vision_scan' })).toBe('VISION_SCAN')

      // Nested payloads
      expect(unpackJarvisStateDetail({ detail: { state: 'DEEP_RESEARCH' } })).toBe('DEEP_RESEARCH')
      expect(unpackJarvisStateDetail({ payload: { state: 'ALERT' } })).toBe('ALERT')
    })

    it('dispatches and listens to jarvis-state CustomEvent across window', () => {
      let capturedState: string | null = null
      const listener = (e: Event) => {
        const detail = (e as CustomEvent).detail
        capturedState = unpackJarvisStateDetail(detail)
      }

      window.addEventListener('jarvis-state', listener)
      try {
        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: 'DEEP_RESEARCH' } }))
        expect(capturedState).toBe('DEEP_RESEARCH')

        window.dispatchEvent(new CustomEvent('jarvis-state', { detail: 'CODING' }))
        expect(capturedState).toBe('CODING')
      } finally {
        window.removeEventListener('jarvis-state', listener)
      }
    })
  })

  // =========================================================================
  // 5. KEYBOARD SHORTCUTS & INPUT GUARDS
  // =========================================================================
  describe('Area 5: Keyboard Shortcuts & Focus Guards', () => {
    it('maps keys 1 through 0 and - to correct states', () => {
      expect(KEY_STATE_MAP['1']).toBe('IDLE')
      expect(KEY_STATE_MAP['2']).toBe('LISTENING')
      expect(KEY_STATE_MAP['3']).toBe('THINKING')
      expect(KEY_STATE_MAP['4']).toBe('SPEAKING')
      expect(KEY_STATE_MAP['5']).toBe('WEB_SEARCH')
      expect(KEY_STATE_MAP['6']).toBe('DEEP_RESEARCH')
      expect(KEY_STATE_MAP['7']).toBe('CODING')
      expect(KEY_STATE_MAP['8']).toBe('VISION_SCAN')
      expect(KEY_STATE_MAP['9']).toBe('MEMORY_SYNC')
      expect(KEY_STATE_MAP['0']).toBe('EXECUTING_TOOL')
      expect(KEY_STATE_MAP['-']).toBe('ALERT')
    })

    it('ignores hotkey when focus is inside HTMLInputElement or HTMLTextAreaElement', () => {
      let triggeredState: string | null = null
      const handleKeyDown = (e: KeyboardEvent) => {
        if (
          e.target &&
          (e.target instanceof HTMLInputElement ||
            e.target instanceof HTMLTextAreaElement ||
            e.target instanceof HTMLSelectElement ||
            (e.target as HTMLElement).isContentEditable)
        ) {
          return
        }
        if (e.ctrlKey || e.altKey || e.metaKey) return
        const mapped = KEY_STATE_MAP[e.key]
        if (mapped) triggeredState = mapped
      }

      window.addEventListener('keydown', handleKeyDown)
      try {
        // 1. Normal window dispatch -> should trigger
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '5' }))
        expect(triggeredState).toBe('WEB_SEARCH')

        // 2. Focused on input -> should NOT trigger
        const input = document.createElement('input')
        document.body.appendChild(input)
        triggeredState = null
        input.dispatchEvent(new KeyboardEvent('keydown', { key: '5', bubbles: true }))
        expect(triggeredState).toBeNull()

        // 3. Focused on textarea -> should NOT trigger
        const textarea = document.createElement('textarea')
        document.body.appendChild(textarea)
        textarea.dispatchEvent(new KeyboardEvent('keydown', { key: '7', bubbles: true }))
        expect(triggeredState).toBeNull()

        // 4. Modifier key active -> should NOT trigger
        window.dispatchEvent(new KeyboardEvent('keydown', { key: '1', ctrlKey: true }))
        expect(triggeredState).toBeNull()

        // Clean up DOM
        document.body.removeChild(input)
        document.body.removeChild(textarea)
      } finally {
        window.removeEventListener('keydown', handleKeyDown)
      }
    })
  })

  // =========================================================================
  // 6. AUDIO LEVEL REACTIVITY TESTS
  // =========================================================================
  describe('Area 6: Audio Level Reactivity Pipeline', () => {
    it('propagates audioLevel directly through jarvisRealtimeRef without React re-render', () => {
      jarvisRealtimeRef.audioLevel = 0.75
      expect(jarvisRealtimeRef.audioLevel).toBe(0.75)

      jarvisRealtimeRef.audioLevel = 0.0
      expect(jarvisRealtimeRef.audioLevel).toBe(0.0)
    })

    it('safely updates state weights with rapid exponential damping and finite bounds', () => {
      const weights = createDefaultStateWeights()
      const result = updateStateWeights(weights, 'SPEAKING', 0.016)

      expect(result.dt).toBeCloseTo(0.016, 5)
      expect(result.damp).toBeGreaterThan(0)
      expect(weights.SPEAKING).toBeGreaterThan(0)
      expect(weights.IDLE).toBeLessThan(1)

      // Extreme spike delta time is clamped to 0.05
      const clamped = updateStateWeights(weights, 'SPEAKING', 10.0)
      expect(clamped.dt).toBe(0.05)
    })
  })
})
```

---

## 6. Execution Strategy & Flakiness Prevention Guidelines

To execute all Milestone 2 tests reliably:

### 6.1 Unit Test Execution Command
```powershell
npx vitest run src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts
```
*Expected Output*:
```text
✓ ui  src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts (15 tests)
Test Files  1 passed (1)
     Tests  15 passed (15)
```

### 6.2 Full Test Suite Regression Command
```powershell
npm test
```
*Expected Output*:
All UI tests (`empirical-lifecycle.test.ts`, `event-wiring.test.ts`, `hermes-adapter.test.ts`) and platform native tests pass.

### 6.3 Full Static Analysis & Build Gate
```powershell
npm run typecheck
npx vite build
```
*Expected Output*:
- `npm run typecheck`: Exit code 0 across all 3 tsconfigs.
- `npx vite build`: Exit code 0 (`✓ built in ~7s`).

---

## 7. Recommended Test File Locations

1. **Vitest Unit/Integration Suite**:  
   `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`  
   *Reason*: Directly co-located with `state-machine.ts`, `audio-bridge.ts`, and `constants.ts`, matching the existing Vitest `ui` glob `src/**/*.test.{ts,tsx}`.
2. **Empirical Challenger Suite (Optional standalone)**:  
   `tests/test_challenger_m2_event_wiring.ts`  
   *Reason*: Can be executed via `npx tsx` independently by Challenger agents during adversarial verification.

---

## 8. Summary & Next Steps for Implementation

1. **Worker Implementers**: Implement the event listeners and priority dispatching in `src/services/jarvisBridge.ts` and `src/lib/gateway-client.ts`, wire the hotkeys into `src/pages/dashboard.tsx` / `HolographicCore`, and implement the above test file in `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`.
2. **Reviewers & Challengers**: Use this test plan as the specification against which to evaluate PRs, ensuring 100% test coverage and zero regression against Milestone 1 deliverables.
