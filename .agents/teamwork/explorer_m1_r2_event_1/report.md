# Investigation & Fix Strategy Report: Defect D2 CustomEvent Detail Unpacking

**Agent**: Explorer M1 R2 Event (`explorer_m1_r2_event_1`)  
**Iteration**: 2 (Milestone 1 Remediation)  
**Target File**: `src/components/dashboard/holographic-core/holographic-core-scene.tsx` (lines 94–98)  
**Parent Orchestrator**: `b204d4ed-af14-4d46-bc7b-8d5d589f3895`  
**Date**: November 11, 2026  

---

## 1. Executive Summary

In Milestone 1, `src/components/dashboard/holographic-core/holographic-core-scene.tsx` established a window event listener for `jarvis-state` to enable runtime switching of the 11 holographic states. In lines 94–98:

```typescript
const handleJarvisState = (e: Event) => {
  const customDetail = (e as CustomEvent).detail
  if (customDetail) {
    realtimeBusState.current = String(customDetail)
  }
}
```

When an event is dispatched per `PROJECT.md` line 62:
```typescript
window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: HolographicState } }));
```
The expression `String(customDetail)` evaluates to the literal string `"[object Object]"`.

### Critical Impact & Cascading Failure:
1. **Normalization Failure**: In `resolveActiveState()`, `normalizeStateName("[object Object]")` yields `null`.
2. **Ref Shadowing Corruption**: In `holographic-core-scene.tsx` line 175:
   ```typescript
   const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
   ```
   Because `"[object Object]"` is a non-empty string, it is truthy. It permanently shadows and blocks valid voice states streaming from `jarvisRealtimeRef.voiceState` (`@/services/jarvisBridge.ts`).
3. **Fallback to IDLE**: As `normalizeStateName("[object Object]")` fails, arbitration drops to Level 6 (`IDLE`), completely ignoring the dispatched state change.

---

## 2. Codebase Ingestion & Specification Survey

### 2.1 Dispatched Event Formats Across the Project

An exhaustive search across the codebase reveals two competing event formats currently in use:

| Source | File & Line | Dispatched Payload Shape | Example |
|---|---|---|---|
| **Specification Contract** | `orchestrator_1/PROJECT.md:62` | Object payload with `state` property | `{ detail: { state: 'ALERT' } }` |
| **Hermes Gateway Adapter** | `src/services/hermes-adapter.ts:60,65,71` | String primitive (aliases & uppercase) | `{ detail: 'SPEAKING' }`, `{ detail: 'LISTEN' }`, `{ detail: 'PROCESSING' }` |
| **Gateway Client Bridge** | `src/lib/gateway-client.ts:228,230,238` | String primitive | `{ detail: 'IDLE' }`, `{ detail: 'SPEAKING' }` |
| **JARVIS Voice AI Service** | `src/services/jarvis-voice-ai.ts:245` | String primitive | `{ detail: 'SPEAKING' }` |
| **Voice Bridge Service** | `src/services/jarvisBridge.ts:169` | String primitive | `{ detail: 'SPEAKING' }` |
| **Keyboard Test Shortcuts** | `holographic-core-scene.tsx:113` | String primitive | `{ detail: 'CODING' }` |

### 2.2 Normalization Capabilities (`state-machine.ts`)

`normalizeStateName(raw: string | null | undefined)` in `state-machine.ts` already handles:
- Exact canonical uppercase matches (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WEB_SEARCH`, `DEEP_RESEARCH`, `CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`, `ALERT`).
- Case-insensitivity (`listening` -> `LISTENING`).
- Leading/trailing whitespace (`"  SPEAKING  "` -> `SPEAKING`).
- Common aliases:
  - `LISTEN`, `HEARING` -> `LISTENING`
  - `THINK`, `PROCESSING`, `REASONING` -> `THINKING`
  - `SPEAK`, `TALKING` -> `SPEAKING`
  - `SEARCH`, `WEB`, `BROWSE` -> `WEB_SEARCH`
  - `RESEARCH`, `DEEP` -> `DEEP_RESEARCH`
  - `CODE`, `CODING_TOOL` -> `CODING`
  - `VISION`, `SCAN`, `CAMERA` -> `VISION_SCAN`
  - `MEMORY`, `SYNC`, `RECALL` -> `MEMORY_SYNC`
  - `TOOL`, `EXECUTE`, `EXECUTING` -> `EXECUTING_TOOL`
  - `ERROR`, `WARN`, `WARNING`, `CRITICAL` -> `ALERT`
  - `STANDBY`, `DEFAULT` -> `IDLE`

However, `normalizeStateName` only accepts a `string | null | undefined`. If passed an object or if `String(object)` yields `"[object Object]"`, it returns `null`.

---

## 3. Comprehensive Payload Taxonomy & Unpacking Requirements

To make the event listener robust against all existing and future dispatch formats, `handleJarvisState` must safely unpack:

1. **String Primitives**:
   - `'THINKING'`, `'speaking'`, `'  LISTEN  '`
2. **Object Payloads (`PROJECT.md` Contract)**:
   - `{ state: 'THINKING' }`, `{ state: 'speaking' }`, `{ state: 'PROCESSING' }`
3. **Common Event Payload Variations**:
   - `{ voiceState: 'speaking' }` (dispatched by voice adapters)
   - `{ status: 'ALERT' }` (system monitor alerts)
   - `{ value: 'IDLE' }`
   - `{ name: 'CODING' }`
   - `{ mode: 'VISION_SCAN' }`
4. **Nested Payloads & Wrapper Events**:
   - Redux/Flux action style: `{ payload: { state: 'CODING' } }` or `{ payload: 'CODING' }`
   - Nested detail re-dispatch: `{ detail: { state: 'ALERT' } }` or `{ detail: 'ALERT' }`
5. **Objects with Custom `.toString()`**:
   - String objects or enum wrappers where `String(obj) !== '[object Object]'`
6. **Explicit Reset Signals**:
   - `{ reset: true }` or `{ state: null }`: should safely clear `realtimeBusState.current` back to `null`, allowing `jarvisRealtimeRef.voiceState` to take precedence again.
7. **Malformed / Invalid Payloads**:
   - `null`, `undefined`, numbers (`42`), booleans (`true`), arbitrary objects (`{ foo: 'bar' }`), cyclic objects.
   - **Requirement**: Must NOT throw, and must NOT update `realtimeBusState.current` to an invalid or unparseable value (preventing shadowing of `jarvisRealtimeRef.voiceState`).

---

## 4. Proposed Fix Strategy

### 4.1 Unpack Logic Specification: `unpackJarvisStateDetail`

We define an unpacking algorithm with cycle protection:

```typescript
/**
 * Safely unpacks any CustomEvent detail payload into a validated HolographicState.
 * Supports string primitives, object payloads ({ state }), common aliases,
 * nested wrappers, and explicitly normalizes all candidates.
 */
export function unpackJarvisStateDetail(detail: unknown, depth = 0): HolographicState | null {
  if (detail == null || depth > 3) {
    return null
  }

  // 1. Direct string primitive
  if (typeof detail === 'string') {
    return normalizeStateName(detail)
  }

  // 2. Object payloads
  if (typeof detail === 'object') {
    const record = detail as Record<string, unknown>

    // Candidate properties in priority order
    const candidateKeys = [
      'state',
      'voiceState',
      'status',
      'value',
      'name',
      'mode',
      'payload',
    ] as const

    for (const key of candidateKeys) {
      const val = record[key]
      if (typeof val === 'string') {
        const normalized = normalizeStateName(val)
        if (normalized) return normalized
      } else if (typeof val === 'object' && val !== null) {
        const nestedResult = unpackJarvisStateDetail(val, depth + 1)
        if (nestedResult) return nestedResult
      }
    }

    // Check nested detail wrapper e.g. { detail: ... }
    if ('detail' in record && record.detail !== undefined && record.detail !== detail) {
      const nestedResult = unpackJarvisStateDetail(record.detail, depth + 1)
      if (nestedResult) return nestedResult
    }

    // Check custom toString() implementation (e.g. String object or enum)
    try {
      const str = String(detail)
      if (str && str !== '[object Object]' && typeof str === 'string') {
        const normalized = normalizeStateName(str)
        if (normalized) return normalized
      }
    } catch {
      // Ignore toString errors on eccentric prototypes
    }
  }

  return null
}
```

### 4.2 Reset Signal Handling

If an event explicitly dispatches a reset or null state:
```typescript
if (
  customDetail &&
  typeof customDetail === 'object' &&
  ('reset' in customDetail || ('state' in customDetail && (customDetail as Record<string, unknown>).state === null))
) {
  realtimeBusState.current = null
  return
}
```
This cleanly restores baseline audio/voice reactivity without requiring component remounting.

---

## 5. Concrete Code Implementation Options

### Option A: Self-Contained in `holographic-core-scene.tsx` (Recommended Primary)

This option keeps all changes strictly contained within `src/components/dashboard/holographic-core/holographic-core-scene.tsx` while importing `normalizeStateName` from `./state-machine`.

#### Step 1: Update Imports in `holographic-core-scene.tsx` (Line 30)

```diff
--- a/src/components/dashboard/holographic-core/holographic-core-scene.tsx
+++ b/src/components/dashboard/holographic-core/holographic-core-scene.tsx
@@ -29,6 +29,7 @@ import {
   calculateRingSpeed,
   createDefaultStateWeights,
+  normalizeStateName,
   resolveActiveState,
   StateTransitionPulseTracker,
   updateStateWeights,
```

#### Step 2: Add `unpackJarvisStateDetail` and Update `handleJarvisState` (Lines 94–99)

```diff
--- a/src/components/dashboard/holographic-core/holographic-core-scene.tsx
+++ b/src/components/dashboard/holographic-core/holographic-core-scene.tsx
@@ -91,10 +91,25 @@ const HolographicCoreInner: React.FC<HolographicCoreInnerProps> = (props) => {
   // Event bus and keyboard shortcut listener
   const realtimeBusState = useRef<string | null>(null)
   useEffect(() => {
     const handleJarvisState = (e: Event) => {
       const customDetail = (e as CustomEvent).detail
-      if (customDetail) {
-        realtimeBusState.current = String(customDetail)
-      }
+      if (!customDetail) return
+
+      // Allow explicit reset: { reset: true } or { state: null }
+      if (
+        typeof customDetail === 'object' &&
+        ('reset' in customDetail || ('state' in customDetail && (customDetail as Record<string, unknown>).state === null))
+      ) {
+        realtimeBusState.current = null
+        return
+      }
+
+      const unpacked = unpackJarvisStateDetail(customDetail)
+      if (unpacked) {
+        realtimeBusState.current = unpacked
+      }
     }
```

And define `unpackJarvisStateDetail` at the top or helper section of `holographic-core-scene.tsx`.

---

### Option B: Export `unpackJarvisStateDetail` from `state-machine.ts` (Modular Architecture)

Placing `unpackJarvisStateDetail` in `src/components/dashboard/holographic-core/state-machine.ts`:
1. Co-locates all state string parsing and normalization logic in `state-machine.ts`.
2. Makes `unpackJarvisStateDetail` directly unit-testable in Node / Vitest without React Three Fiber rendering dependencies.
3. Automatically re-exports via `src/components/dashboard/holographic-core/index.ts`.

In `state-machine.ts`:
```typescript
export function unpackJarvisStateDetail(detail: unknown, depth = 0): HolographicState | null { ... }
```

In `holographic-core-scene.tsx`:
```typescript
import {
  ...
  normalizeStateName,
  unpackJarvisStateDetail,
  ...
} from './state-machine'
```

---

## 6. Unit Test Specification for Empirical Verification

To verify that Defect D2 is completely resolved, the following tests should be added to `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`:

```typescript
describe('Area 1.4: CustomEvent Detail Unpacking (Defect D2 Verification)', () => {
  it('unpacks string payloads with normalization', () => {
    expect(unpackJarvisStateDetail('THINKING')).toBe('THINKING')
    expect(unpackJarvisStateDetail('speaking')).toBe('SPEAKING')
    expect(unpackJarvisStateDetail('LISTEN')).toBe('LISTENING')
    expect(unpackJarvisStateDetail('PROCESSING')).toBe('THINKING')
  })

  it('unpacks PROJECT.md object payload { state: HolographicState }', () => {
    expect(unpackJarvisStateDetail({ state: 'THINKING' })).toBe('THINKING')
    expect(unpackJarvisStateDetail({ state: 'ALERT' })).toBe('ALERT')
    expect(unpackJarvisStateDetail({ state: 'listening' })).toBe('LISTENING')
    expect(unpackJarvisStateDetail({ state: 'LISTEN' })).toBe('LISTENING')
  })

  it('unpacks alternative key shapes (voiceState, status, value, name, mode)', () => {
    expect(unpackJarvisStateDetail({ voiceState: 'speaking' })).toBe('SPEAKING')
    expect(unpackJarvisStateDetail({ status: 'ERROR' })).toBe('ALERT')
    expect(unpackJarvisStateDetail({ value: 'CODING' })).toBe('CODING')
    expect(unpackJarvisStateDetail({ name: 'VISION_SCAN' })).toBe('VISION_SCAN')
    expect(unpackJarvisStateDetail({ mode: 'MEMORY_SYNC' })).toBe('MEMORY_SYNC')
  })

  it('unpacks nested payload and detail wrappers', () => {
    expect(unpackJarvisStateDetail({ payload: { state: 'CODING' } })).toBe('CODING')
    expect(unpackJarvisStateDetail({ detail: { state: 'ALERT' } })).toBe('ALERT')
    expect(unpackJarvisStateDetail({ detail: 'SPEAKING' })).toBe('SPEAKING')
  })

  it('safely rejects invalid or malformed payloads without throwing', () => {
    expect(unpackJarvisStateDetail(null)).toBeNull()
    expect(unpackJarvisStateDetail(undefined)).toBeNull()
    expect(unpackJarvisStateDetail('')).toBeNull()
    expect(unpackJarvisStateDetail(12345)).toBeNull()
    expect(unpackJarvisStateDetail(true)).toBeNull()
    expect(unpackJarvisStateDetail({})).toBeNull()
    expect(unpackJarvisStateDetail({ foo: 'bar' })).toBeNull()
    expect(unpackJarvisStateDetail({ state: 'INVALID_STATE_XYZ' })).toBeNull()
  })

  it('safely handles circular references without stack overflow', () => {
    const cyclic: any = { state: 'THINKING' }
    cyclic.self = cyclic
    expect(unpackJarvisStateDetail(cyclic)).toBe('THINKING')
  })
})
```

---

## 7. Downstream Advisory: Milestone 2 Event Bus Considerations

While this fix completely resolves Defect D2 within `holographic-core-scene.tsx`, the survey identified:
- `src/components/dashboard/mini-overlay.tsx` lines 46–47 checks `if (e.detail === 'SPEAKING')`.
- When Milestone 2 transitions the entire app to dispatching `{ state: HolographicState }`, `mini-overlay.tsx` should also be upgraded using `unpackJarvisStateDetail`.
- For Milestone 1, fixing `holographic-core-scene.tsx` restores full fidelity and specification compliance for the 3D core visualizer.
