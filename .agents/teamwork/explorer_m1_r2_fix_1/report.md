# Investigation Report: Defect D1 Fix Strategy & Mathematical Bounds Hardening (Iteration 2)

**Agent**: Explorer (`explorer_m1_r2_fix_1`)  
**Parent Orchestrator**: `b204d4ed-af14-4d46-bc7b-8d5d589f3895`  
**Milestone**: Milestone 1 Iteration 2 (Remediation & Hardening)  
**Date**: November 11, 2026  
**Target Codebase**: `e:\Projects\J.A.R.V.I.S Electron App`  

---

## Executive Summary

This investigation establishes the exact, production-ready fix strategy for Defect D1 (the `activeTool` regex precedence flaw in `state-machine.ts`) and two critical mathematical hardening protections identified during the Milestone 1 audit (delta time lower-bound clamping in `updateStateWeights` and audio level boundary normalization in `audio-bridge.ts`).

Additionally, this report outlines the necessary test harness alignment in `empirical-lifecycle.test.ts` and the event bus detail payload handling in `holographic-core-scene.tsx` to ensure that all 24+ vitest tests, typecheck validations, and production builds pass cleanly with 100% specification compliance.

---

## 1. Problem Breakdown & Evidence Chain

### 1.1 Defect D1: Regex Precedence Flaw in `activeTool` State Arbitration
- **Target File**: `src/components/dashboard/holographic-core/state-machine.ts`
- **Location**: Lines 90–99
- **Existing Implementation**:
  ```typescript
  // Level 3: Active Tool Execution Mapping
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    const tool = props.activeTool.toLowerCase()
    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
    if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
    if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
    if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
    return 'EXECUTING_TOOL'
  }
  ```
- **Root Cause Analysis**:
  The English word `"researcher"` contains the substring `"search"`:
  $$\text{"researcher"} = \text{"re"} + \mathbf{\text{"search"}} + \text{"er"}$$
  The regex on line 93 (`/search|browse|crawl|google|web/i`) performs an un-anchored substring match. Consequently, when `props.activeTool` is `"gpt_researcher_query"` (or any tool name containing `"research"`), the `/search/` branch evaluates to `true` first. Line 94 is never reached.
- **Specification Conflict**:
  `orchestrator_1/PROJECT.md` line 68 explicitly specifies:
  ```markdown
  - `crawl4ai_*`, `browser_use_*` -> `WEB_SEARCH`
  - `gpt_researcher_*`, `delegate_task` -> `DEEP_RESEARCH`
  ```
  Under the existing code, `gpt_researcher` maps to `WEB_SEARCH` (cyan/teal particle cloud with horizontal scanner ring), completely preventing the visualizer from entering `DEEP_RESEARCH` (purple/indigo palette with 3 concentric knowledge shells).

### 1.2 Mathematical Vulnerability 1: Delta Time Lower Bound Clamping
- **Target File**: `src/components/dashboard/holographic-core/state-machine.ts`
- **Location**: Lines 139–154 (`updateStateWeights`)
- **Existing Implementation**:
  ```typescript
  export function updateStateWeights(
    weights: StateWeights,
    activeState: HolographicState,
    delta: number
  ): { damp: number; dt: number } {
    const dt = Math.min(0.05, delta)
    const damp = 1 - Math.exp(-6.2 * dt)

    for (let i = 0; i < STATE_KEYS.length; i++) {
      const key = STATE_KEYS[i]
      const target = activeState === key ? 1 : 0
      weights[key] += (target - weights[key]) * damp
    }

    return { damp, dt }
  }
  ```
- **Root Cause & Mathematical Failure**:
  Line 144 only clamps from above (`Math.min(0.05, delta)`). If `delta < 0` occurs (e.g. OS system clock rollback, negative timestamp jitter, or NTP sync adjustments during rendering):
  $$dt < 0 \implies -6.2 \cdot dt > 0 \implies \exp(-6.2 \cdot dt) > 1 \implies damp = 1 - \exp(-6.2 \cdot dt) < 0$$
  For $delta = -0.016\text{ s}$, $damp = 1 - \exp(0.0992) = -0.1043$.
  In the update step:
  $$weights[key] \mathrel{+}= (target - weights[key]) \cdot damp$$
  Because $damp < 0$, weights move in the *opposite* direction of the target! Active states decrease, inactive states increase, destroying the partition of unity ($\sum w_k = 1.0$) and causing mathematical divergence.
  Furthermore, if `delta` is non-finite (`NaN`), `Math.min(0.05, NaN)` yields `NaN`, contaminating all 11 state weights with `NaN`.

### 1.3 Mathematical Vulnerability 2: Audio Gain Overdrive & Input Normalization
- **Target File**: `src/components/dashboard/holographic-core/audio-bridge.ts`
- **Location**: Lines 59–69
- **Existing Implementation**:
  ```typescript
  // 2. Mutable Realtime WebSocket & Prop Audio Level Sampling
  const externalLevel = Math.max(
    jarvisRealtimeRef.audioLevel || 0,
    propAudioLevel || 0
  )
  if (externalLevel > 0) {
    rawBass = Math.max(rawBass, externalLevel * 0.95)
    rawMid = Math.max(rawMid, externalLevel * 0.85)
    rawTreble = Math.max(rawTreble, externalLevel * 0.75)
  }
  ```
- **Root Cause & Physical Distortion**:
  1. `externalLevel` has no upper bound. If callers pass unnormalized audio levels (e.g. $audioLevel = 5.0$ or $10.0$ from an un-clamped gain slider or audio driver), `rawBass` scales to $4.75$. In `SPEAKING` mode, audio level directly drives particle corona expansion ($r = BASE\_RADIUS \cdot (1 + bass \cdot 0.35 + \dots)$).
  2. As empirically demonstrated in Challenger 1's report (Observation A2), un-clamped audio pushes particle displacement out to $r = 5.108$ units. Since the Three.js perspective camera is positioned at $[0, 0, 5.1]$, particles collide with and clip through the camera lens.
  3. If `propAudioLevel` is `NaN`, `Math.max(0, NaN)` evaluates to `NaN` in JavaScript, corrupting audio reactivity.

### 1.4 Secondary Vulnerability: CustomEvent Detail Object Handling
- **Target File**: `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
- **Location**: Lines 94–99
- **Existing Implementation**:
  ```typescript
  const handleJarvisState = (e: Event) => {
    const customDetail = (e as CustomEvent).detail
    if (customDetail) {
      realtimeBusState.current = String(customDetail)
    }
  }
  ```
- **Issue**:
  `PROJECT.md` line 62 documents dispatching `{ detail: { state: HolographicState } }`. If an object is dispatched, `String(customDetail)` becomes `"[object Object]"`, failing state normalization.

---

## 2. Exact Remediation Strategy

### 2.1 Fix 1: Regex Precedence in `state-machine.ts`
Evaluate `DEEP_RESEARCH` (`/research|delegate|analyze|investigate/i`) strictly **before** `WEB_SEARCH` (`/search|browse|crawl|google|web/i`).

#### Proposed Replacement (Lines 90–100 of `state-machine.ts`):
```typescript
<<<<
  // Level 3: Active Tool Execution Mapping
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    const tool = props.activeTool.toLowerCase()
    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
    if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
    if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
    if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
    return 'EXECUTING_TOOL'
  }
====
  // Level 3: Active Tool Execution Mapping
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    const tool = props.activeTool.toLowerCase()
    // Check DEEP_RESEARCH before WEB_SEARCH so 'researcher' is not masked by 'search'
    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
    if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
    if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
    if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
    return 'EXECUTING_TOOL'
  }
>>>>
```

### 2.2 Fix 2: Delta Time Clamping in `state-machine.ts`
Apply two-sided clamping $[0, 0.05]$ to `delta` with non-finite safety guard:

#### Proposed Replacement (Lines 139–154 of `state-machine.ts`):
```typescript
<<<<
export function updateStateWeights(
  weights: StateWeights,
  activeState: HolographicState,
  delta: number
): { damp: number; dt: number } {
  const dt = Math.min(0.05, delta)
  const damp = 1 - Math.exp(-6.2 * dt)

  for (let i = 0; i < STATE_KEYS.length; i++) {
    const key = STATE_KEYS[i]
    const target = activeState === key ? 1 : 0
    weights[key] += (target - weights[key]) * damp
  }

  return { damp, dt }
}
====
export function updateStateWeights(
  weights: StateWeights,
  activeState: HolographicState,
  delta: number
): { damp: number; dt: number } {
  const safeDt = Number.isFinite(delta) ? Math.max(0, Math.min(0.05, delta)) : 0
  const damp = 1 - Math.exp(-6.2 * safeDt)

  for (let i = 0; i < STATE_KEYS.length; i++) {
    const key = STATE_KEYS[i]
    const target = activeState === key ? 1 : 0
    weights[key] += (target - weights[key]) * damp
  }

  return { damp, dt: safeDt }
}
>>>>
```

### 2.3 Fix 3: Audio Input Normalization & Clamping in `audio-bridge.ts`
Safely sanitize inputs against `NaN` and clamp `externalLevel` strictly to $[0.0, 1.0]$:

#### Proposed Replacement (Lines 59–69 of `audio-bridge.ts`):
```typescript
<<<<
    // 2. Mutable Realtime WebSocket & Prop Audio Level Sampling
    const externalLevel = Math.max(
      jarvisRealtimeRef.audioLevel || 0,
      propAudioLevel || 0
    )
    if (externalLevel > 0) {
      rawBass = Math.max(rawBass, externalLevel * 0.95)
      rawMid = Math.max(rawMid, externalLevel * 0.85)
      rawTreble = Math.max(rawTreble, externalLevel * 0.75)
    }
====
    // 2. Mutable Realtime WebSocket & Prop Audio Level Sampling
    const refLevel = Number.isFinite(jarvisRealtimeRef.audioLevel) ? (jarvisRealtimeRef.audioLevel as number) : 0
    const propLevel = Number.isFinite(propAudioLevel) ? (propAudioLevel as number) : 0
    const rawExternal = Math.max(refLevel, propLevel)
    const externalLevel = Math.min(1.0, Math.max(0, rawExternal))

    if (externalLevel > 0) {
      rawBass = Math.max(rawBass, externalLevel * 0.95)
      rawMid = Math.max(rawMid, externalLevel * 0.85)
      rawTreble = Math.max(rawTreble, externalLevel * 0.75)
    }
>>>>
```

### 2.4 Fix 4: CustomEvent Detail Object Unpacking in `holographic-core-scene.tsx`
Safely unpack `detail.state` when objects are passed to `jarvis-state`:

#### Proposed Replacement (Lines 93–100 of `holographic-core-scene.tsx`):
```typescript
<<<<
    const handleJarvisState = (e: Event) => {
      const customDetail = (e as CustomEvent).detail
      if (customDetail) {
        realtimeBusState.current = String(customDetail)
      }
    }
====
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
>>>>
```

---

## 3. Test Suite Alignment in `empirical-lifecycle.test.ts`

Currently, `empirical-lifecycle.test.ts` lines 184–199 explicitly tests and asserts the bug as a defect reproduction case:
```typescript
it('Level 3 Defect Reproduction: gpt_researcher incorrectly matches /search/ before /research/', () => {
  ...
  expect(actualState).toBe('WEB_SEARCH') // Demonstrates the substring masking bug
})
```
When Fix 1 is applied, `actualState` becomes `'DEEP_RESEARCH'`, which will cause this reproduction test to fail.
The test must be updated to assert the fixed behavior:

#### Proposed Test Update:
```typescript
<<<<
    it('Level 3 Defect Reproduction: gpt_researcher incorrectly matches /search/ before /research/', () => {
      // In PROJECT.md line 68: gpt_researcher_* -> DEEP_RESEARCH
      // In state-machine.ts line 93: /search|browse|crawl|google|web/i.test(tool) matches 'research' because 'research' contains 'search'!
      const props: SphereProps = {
        activeTool: 'gpt_researcher_query',
      }
      const actualState = resolveActiveState(props)

      // Empirically document the flaw: actual is WEB_SEARCH, whereas PROJECT.md spec is DEEP_RESEARCH
      const matchesSearchRegex = /search|browse|crawl|google|web/i.test('gpt_researcher_query')
      expect(matchesSearchRegex).toBe(true)
      expect(actualState).toBe('WEB_SEARCH') // Demonstrates the substring masking bug
      console.warn(
        `[CRITICAL DEFECT CONFIRMED] tool='gpt_researcher_query' resolved to '${actualState}', expected 'DEEP_RESEARCH' per PROJECT.md line 68.`
      )
    })
====
    it('Level 3: gpt_researcher correctly maps to DEEP_RESEARCH (resolves D1 substring masking defect)', () => {
      // In PROJECT.md line 68: gpt_researcher_* -> DEEP_RESEARCH
      const props: SphereProps = {
        activeTool: 'gpt_researcher_query',
      }
      const actualState = resolveActiveState(props)
      expect(actualState).toBe('DEEP_RESEARCH')
    })
>>>>
```

Also, add `'gpt_researcher_query'` to the canonical test cases in lines 148–167:
```typescript
{ tool: 'gpt_researcher_query', expected: 'DEEP_RESEARCH' },
```

---

## 4. Implementation Validation Matrix

| Change Area | Affected File | Line # | Before Behavior | Target Behavior | Risk Level |
|---|---|---|---|---|---|
| D1 Regex Precedence | `state-machine.ts` | 93–94 | `gpt_researcher_*` -> `WEB_SEARCH` | `gpt_researcher_*` -> `DEEP_RESEARCH` | Zero risk, restores spec |
| Delta Time Clamping | `state-machine.ts` | 144 | $dt < 0 \implies damp < 0$ (divergence) | $dt \in [0, 0.05] \implies damp \ge 0$ | Zero risk, eliminates clock rollback bug |
| Audio Normalization | `audio-bridge.ts` | 60–63 | $audioLevel > 1.0$ clips camera | $externalLevel \in [0.0, 1.0]$ | Zero risk, maintains optical safety |
| Event Detail Unpack | `holographic-core-scene.tsx` | 94–98 | `{ state: '...' }` -> `"[object Object]"` | Unpacks `detail.state` | Zero risk, backward-compatible |
| Test Assertions | `empirical-lifecycle.test.ts` | 184–199 | Asserts defective `'WEB_SEARCH'` | Asserts correct `'DEEP_RESEARCH'` | Zero risk, reflects true contract |

---

## 5. Verification Commands for Iteration 2

After implementation, execute the following commands to confirm full system integrity:

```powershell
# 1. Run full Vitest lifecycle and state-machine suite
npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts

# 2. Run Challenger Math and Physics suite (38 empirical assertions)
npx tsx tests/test_challenger_m1_math_physics.ts

# 3. Run Challenger Adversarial Stress harness (includes negative dt and audio overdrive)
npx tsx tests/test_challenger_m1_adversarial_stress.ts

# 4. Run TypeScript project typecheck
npm run typecheck

# 5. Run Production Vite build
npx vite build
```
