# Test Suite Alignment and Regression Safety Report (Milestone 1 — Iteration 2)

- **Agent**: Explorer (`explorer_m1_r2_tests_1`)
- **Mission**: Align test suites and verify regression safety for Milestone 1, Iteration 2
- **Target Files**:
  - `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
  - `src/components/dashboard/holographic-core/state-machine.ts`
  - `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
  - `src/components/dashboard/holographic-core/audio-bridge.ts`
  - `tests/test_challenger_m1_math_physics.ts`
- **Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App`
- **Date**: 2026-11-11

---

## 1. Executive Summary

During Milestone 1 Iteration 1 review, two high-priority findings and a defensive hardening item were identified:
1. **Finding D1**: In `state-machine.ts`, the `activeTool` classification regex for `WEB_SEARCH` (`/search|browse|crawl|google|web/i`) preceded `DEEP_RESEARCH` (`/research|delegate|analyze|investigate/i`). Because the word `"research"` contains `"search"`, tools like `gpt_researcher_*` matched `WEB_SEARCH` instead of `DEEP_RESEARCH` (specified in `PROJECT.md` line 68).
2. **Test Suite Status**: In Iteration 1, Challenger 2 authored an adversarial test in `empirical-lifecycle.test.ts` (test 5, lines 184–199) titled `"Level 3 Defect Reproduction: gpt_researcher incorrectly matches /search/ before /research/"` which asserted `expect(actualState).toBe('WEB_SEARCH')` to document the defect. Flipping the regex order fixes the underlying runtime behavior (`actualState` becomes `'DEEP_RESEARCH'`), but this test must be aligned to assert `expect(actualState).toBe('DEEP_RESEARCH')`. With that single assertion updated, all 24 tests in `empirical-lifecycle.test.ts` pass cleanly.
3. **Regression Safety on Challenger 1 Harness**: `tests/test_challenger_m1_math_physics.ts` (38 assertions across 6 suites) does not invoke `resolveActiveState` or tool mapping at all. Its physics, geometry, damping, cardiac, toroidal, and ring calculations are completely independent of tool regexes. All 38 assertions remain 100% passing.
4. **Defensive Hardening Constraints**: When Worker adds lower-bound delta clamping in `updateStateWeights`, Worker must clamp using `Math.max(0, Math.min(0.05, delta))` so that legitimate sub-millisecond deltas (such as `dt = 0.001s` tested in `test_challenger_m1_math_physics.ts` line 392) remain exact.

---

## 2. Line-by-Line Inspection of `empirical-lifecycle.test.ts`

The Vitest test suite `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts` contains exactly **24 test cases** distributed across **5 logical areas**. Below is the complete line-by-line inspection:

### Summary Table of All 24 Tests

| Area | # | Test Name | Lines | SUT Functions | Assertions | Regex Order Impact |
|------|---|-----------|-------|---------------|------------|-------------------|
| **Area 1: 11-State Priority Arbitration** | 1 | `normalizes all 11 canonical states and known aliases correctly` | 41–98 | `normalizeStateName` | 95 total assertions (11 canonical * 3 variations + 29 aliases * 2 + 4 edge cases) | **None** (pure alias map) |
| | 2 | `Level 1: Explicit overrideState / state prop overrides all other levels` | 100–127 | `resolveActiveState` | 3 assertions (overrideState, state prop, invalid string fallback) | **None** (bypasses Level 3) |
| | 3 | `Level 2: Error condition produces ALERT over tools, booleans, and realtime` | 129–145 | `resolveActiveState` | 2 assertions (error string -> ALERT, error: null -> passes through) | **None** (bypasses Level 3) |
| | 4 | `Level 3: activeTool maps tools to distinct canonical states` | 147–182 | `resolveActiveState` | 20 assertions (18 tool names + 2 empty/whitespace falls through) | **None** (all 18 tools disjoint from research/search collisions) |
| | 5 | `Level 3 Defect Reproduction: gpt_researcher incorrectly matches /search/ before /research/` | 184–199 | `resolveActiveState` | 2 assertions (`matchesSearchRegex === true`, `actualState === 'WEB_SEARCH'`) | **DIRECT IMPACT**: Must be aligned to `expect(actualState).toBe('DEEP_RESEARCH')` |
| | 6 | `Level 4: Exhaustive permutations of legacy booleans follow speaking > thinking > listening` | 201–222 | `resolveActiveState` | 8 assertions (all 8 boolean permutations) | **None** (Level 4 legacy flags) |
| | 7 | `Level 5: Realtime voiceState resolves when legacy booleans are inactive` | 224–235 | `resolveActiveState` | 4 assertions (SPEAKING, HEARING -> LISTENING, REASONING -> THINKING, UNKNOWN -> IDLE) | **None** (Level 5 realtime string) |
| | 8 | `Level 6: Fallback resolves strictly to IDLE` | 237–241 | `resolveActiveState` | 3 assertions ({}, null, undefined -> IDLE) | **None** (Level 6 fallback) |
| **Area 2: Rapid State Transitions & Partition of Unity** | 9 | `executes 100 random state transitions verifying partition of unity and convergence` | 248–321 | `updateStateWeights`, `createDefaultStateWeights` | >3,000 assertions (damping formula, finite, bounds [0, 1], partition drift < 1e-5, convergence >= 0.95) | **None** |
| | 10 | `enforces dt clamping at 0.05s to prevent overshoot on frame rate drops` | 323–332 | `updateStateWeights` | 4 assertions (dt=0.05, damp formula, ALERT weight, no overshoot) | **None** |
| | 11 | `verifies twin-beat cardiac shockwave math` | 334–356 | `calculateCardiacBeat` | 104 assertions (systole > 0.99, diastole ~0.68, quiet < 0.01, 100 non-negativity samples) | **None** |
| | 12 | `verifies StateTransitionPulseTracker expansion and decay over 450ms` | 358–385 | `StateTransitionPulseTracker` | 11 assertions (initial inactive, t0 scale/opacity, tHalf scale/opacity, tEnd expired) | **None** |
| | 13 | `verifies ring speeds and base opacities across all 11 states` | 387–401 | `calculateRingSpeed`, `calculateBaseRingOpacity` | 44 assertions (speed > 0, opacity in [0, 1] across all 11 states) | **None** |
| **Area 3: Audio Reactivity Bridge (3-Band FFT & Fallback)** | 14 | `aggregates 3-band FFT bins correctly (Bass 0-15, Mid 16-55, Treble 56-111)` | 418–474 | `AudioReactivityBridge.update` | 12 assertions (mock AnalyserNode for Bass, Mid, Treble, and Unused bins 112-127) | **None** |
| | 15 | `scales scalar audioLevel prop across bass, mid, and treble (0.95, 0.85, 0.75)` | 476–484 | `AudioReactivityBridge.update` | 3 assertions (Bass ~0.76, Mid ~0.68, Treble ~0.60) | **None** |
| | 16 | `activates autonomous speech cadence simulation fallback when speaking without audio feed (< 0.03)` | 486–515 | `AudioReactivityBridge.update` | 300 assertions (non-zero and <= 1.0 across 50 timestamps) | **None** |
| | 17 | `activates attentive synthetic mic pulse fallback when LISTENING without audio feed (< 0.02)` | 517–526 | `AudioReactivityBridge.update` | 90 assertions (non-zero across 30 timestamps) | **None** |
| | 18 | `amplifies live mic sensitivity when LISTENING with active feed (>= 0.02)` | 528–534 | `AudioReactivityBridge.update` | 2 assertions (Bass > 0.15, Mid > 0.15 for 0.1 input) | **None** |
| | 19 | `smooths values exponentially with decay k = 14.0 s^-1` | 536–549 | `AudioReactivityBridge.update` | 2 assertions (1st frame damp step, 20-frame convergence to 0.95) | **None** |
| **Area 4: Procedural Texture Generation** | 20 | `creates volumetric glow texture with 64x64 dimensions, radial gradient, and alpha profile` | 579–592 | `createVolumetricGlowTexture` | 7 assertions (CanvasTexture instance, dimensions 64x64, version > 0, gradient coords, fillRect) | **None** |
| | 21 | `creates backdrop halo texture with 128x128 dimensions, radial gradient, and dark navy profile` | 594–606 | `createBackdropHaloTexture` | 7 assertions (CanvasTexture instance, dimensions 128x128, version > 0, gradient coords, fillRect) | **None** |
| | 22 | `creates and disposes procedural textures without error` | 608–624 | `createProceduralTextures`, `disposeProceduralTextures` | 6 assertions (textures created, dispose called on glow and backdrop, null/undefined safety) | **None** |
| **Area 5: Pointer Orbit Pitch Clamping** | 23 | `strictly clamps pointer orbit pitch angle within [-1.05, +1.05] radians` | 631–657 | `MAX_PITCH_ANGLE` | 6 assertions (+10k px clamped to +1.05, -10k px clamped to -1.05, moderate dy values) | **None** |
| | 24 | `simulates damped pitch rotation convergence within clamp bounds` | 659–671 | Pitch damping loop | 121 assertions (bounds check over 60 frames, final convergence to 1.05) | **None** |

### Detailed Inspection of Test 4 vs Test 5 (Area 1)

In Test 4 (`Level 3: activeTool maps tools to distinct canonical states`, lines 147–182), the following 18 tool strings are tested:
- `google_web_search` -> `WEB_SEARCH`
- `crawl4ai_extract` -> `WEB_SEARCH`
- `browser_use_action` -> `WEB_SEARCH`
- `delegate_task_subagent` -> `DEEP_RESEARCH`
- `data_analyzer` -> `DEEP_RESEARCH`
- `deep_investigate` -> `DEEP_RESEARCH`
- `code_interpreter` -> `CODING`
- `terminal_bash_exec` -> `CODING`
- `shell_command` -> `CODING`
- `file_editor` -> `CODING`
- `camera_stream_read` -> `VISION_SCAN`
- `mediapipe_face_mesh` -> `VISION_SCAN`
- `lidar_depth_scan` -> `VISION_SCAN`
- `memory_sync_checkpoint` -> `MEMORY_SYNC`
- `sqlite_db_query` -> `MEMORY_SYNC`
- `vector_store_recall` -> `MEMORY_SYNC`
- `random_calculator_math` -> `EXECUTING_TOOL`
- `weather_fetcher_api` -> `EXECUTING_TOOL`

**Analysis of Collision Safety**:
- None of the 3 `WEB_SEARCH` tools (`google_web_search`, `crawl4ai_extract`, `browser_use_action`) contain any `DEEP_RESEARCH` keywords (`research`, `delegate`, `analyze`, `investigate`). When the regex order is flipped, they will fail to match `/research|delegate|analyze|investigate/i` and continue straight into `/search|browse|crawl|google|web/i`, returning `WEB_SEARCH`.
- None of the other tool categories (`CODING`, `VISION_SCAN`, `MEMORY_SYNC`, `EXECUTING_TOOL`) match either `DEEP_RESEARCH` or `WEB_SEARCH`.
- Therefore, **all 18 test cases in Test 4 remain 100% PASS** after flipping the regex order.

---

## 3. ActiveTool Regex Inversion Analysis in `state-machine.ts`

### 3.1 Defect Mechanism (Why the Bug Occurred)
In `src/components/dashboard/holographic-core/state-machine.ts` lines 91–99:
```typescript
  // Level 3: Active Tool Execution Mapping
  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
    const tool = props.activeTool.toLowerCase()
    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'      // Line 93
    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH' // Line 94
    if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
    if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
    if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
    return 'EXECUTING_TOOL'
  }
```
In JavaScript regular expressions, `/search/i.test("gpt_researcher_query")` evaluates to `true` because the substring `"search"` is embedded within `"researcher"`:
`"re" + "search" + "er_query"`.
Because line 93 appeared before line 94, any tool with `"research"` in its name was intercepted by line 93 and returned `'WEB_SEARCH'`.

### 3.2 Solution: Flipping the Regex Check Order
By placing the more specific pattern (`DEEP_RESEARCH`) before the broader substring pattern (`WEB_SEARCH`):
```typescript
  // Level 3: Active Tool Execution Mapping
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
Under this ordering:
1. `gpt_researcher_query`:
   - Checks `/research|delegate|analyze|investigate/i`: Matches `"research"` -> Returns `'DEEP_RESEARCH'`. (CORRECT per `PROJECT.md` line 68)
2. `google_web_search`:
   - Checks `/research|delegate|analyze|investigate/i`: Does NOT match.
   - Checks `/search|browse|crawl|google|web/i`: Matches `"search"` and `"google"` and `"web"` -> Returns `'WEB_SEARCH'`. (CORRECT)
3. `crawl4ai_extract`:
   - Checks `/research...`: Does NOT match.
   - Checks `/search...`: Matches `"crawl"` -> Returns `'WEB_SEARCH'`. (CORRECT)

### 3.3 Test Suite Alignment in `empirical-lifecycle.test.ts`
In Iteration 1, Test 5 was written specifically to demonstrate the bug:
```typescript
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
```
When Worker flips the regex in `state-machine.ts`, `resolveActiveState(props)` returns `'DEEP_RESEARCH'`.
If Test 5 is left unchanged, line 195 `expect(actualState).toBe('WEB_SEARCH')` will FAIL.

**Required Alignment for Worker in `empirical-lifecycle.test.ts` lines 184–199**:
```typescript
    it('Level 3: gpt_researcher correctly matches /research/ before /search/ yielding DEEP_RESEARCH', () => {
      // In PROJECT.md line 68: gpt_researcher_* -> DEEP_RESEARCH
      // Verified: /research/ check takes precedence over /search/ to avoid substring collision
      const props: SphereProps = {
        activeTool: 'gpt_researcher_query',
      }
      const actualState = resolveActiveState(props)
      expect(actualState).toBe('DEEP_RESEARCH')
    })
```
With this change:
- All 24 tests in `empirical-lifecycle.test.ts` will pass.
- The defect reproduction test is promoted into a permanent regression test preventing future ordering reversions.

---

## 4. Regression Safety Analysis of `tests/test_challenger_m1_math_physics.ts`

`tests/test_challenger_m1_math_physics.ts` is an empirical verification harness comprising **38 assertions across 6 suites**.

### 4.1 Assertion-by-Assertion Audit

| Suite | Assertion Name | Function Under Test | Dependency on State Machine | Risk |
|---|---|---|---|---|
| **Suite 1: Fibonacci Sphere** | 1.1 Buffer Array Dimensions | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.2 Zero NaN / Zero Inf Sanity | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.3 Normal Vectors Unit Length | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.4 Base Radius Adherence | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.5 Golden Angle Adherence & Polar Moiré Suppression | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.6 Spherical Area Uniformity | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 1.7 Concentric Shell Non-Collision | `buildParticleGeometryData` | None (pure geometry) | 0% |
| **Suite 2: Morph Targets** | 2.1 Lat/Lon Globe Discretization & Clamping | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 2.2 Globe Normals Blending Bounds | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 2.3 Holo-Cube 0.77 Face Boundary Invariance | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 2.4 Cube Beveled Corner Smoothing Profile | `buildParticleGeometryData` | None (pure geometry) | 0% |
| | 2.5 Matrix Rain Column Seeds Bounds | `buildParticleGeometryData` | None (pure geometry) | 0% |
| **Suite 3: Damping Engine** | 3.1 Damping calculation at dt=0.001s | `updateStateWeights` | Exponential damping formula | **0%** (see constraint below) |
| | 3.2 Damping calculation at dt=0.00833s | `updateStateWeights` | Exponential damping formula | 0% |
| | 3.3 Damping calculation at dt=0.01667s | `updateStateWeights` | Exponential damping formula | 0% |
| | 3.4 Damping calculation at dt=0.03333s | `updateStateWeights` | Exponential damping formula | 0% |
| | 3.5 Damping calculation at dt=0.05s | `updateStateWeights` | Exponential damping formula | 0% |
| | 3.6 Damping calculation at dt=0.1s | `updateStateWeights` | Delta clamping (0.05s) | 0% |
| | 3.7 Damping calculation at dt=1.0s | `updateStateWeights` | Delta clamping (0.05s) | 0% |
| | 3.8 Damping calculation at dt=100.0s | `updateStateWeights` | Delta clamping (0.05s) | 0% |
| | 3.9 Delta Time Clamping on Lag Spike (5.0s) | `updateStateWeights` | Delta clamping (0.05s) | 0% |
| | 3.10 Empirical Damping Convergence Half-Life | `updateStateWeights` | Exponential damping formula | 0% |
| | 3.11 Partition of Unity & Zero Overshoot | `updateStateWeights` | Weight summation across 11 states | 0% |
| **Suite 4: Cardiac Shockwave** | 4.1 Primary Systole Peak ("Lub") | `calculateCardiacBeat` | Cardiac formula (tau=0.12) | 0% |
| | 4.2 Secondary Diastole Peak ("Dub") | `calculateCardiacBeat` | Cardiac formula (tau=0.30) | 0% |
| | 4.3 Resting Cardiac Quiescence | `calculateCardiacBeat` | Baseline quiescence | 0% |
| | 4.4 Initial State Inactive | `StateTransitionPulseTracker` | Pulse tracker | 0% |
| | 4.5 Trigger on State Transition | `StateTransitionPulseTracker` | Pulse tracker | 0% |
| | 4.6 Monotonic Expansion & Decay Expiration | `StateTransitionPulseTracker` | Pulse tracker | 0% |
| **Suite 5: Toroidal Flow** | 5.1 Throat and Outer Torus Radii | Toroidal formulas | None | 0% |
| | 5.2 Non-Self-Intersecting Open Throat | Toroidal formulas | None | 0% |
| | 5.3 World Space Radial Bounds | Toroidal formulas | None | 0% |
| | 5.4 Throat Flux Highlight Amplification | Toroidal formulas | None | 0% |
| **Suite 6: Ring & Core Dynamics** | 6.1 11-State Angular Velocities | `calculateRingSpeed` | State-weighted speed | 0% |
| | 6.2 11-State Ring Opacities | `calculateBaseRingOpacity` | State-weighted opacity | 0% |
| | 6.3 Ring Radius Nesting & Clearance | `RING*_CONFIG` constants | Nesting hierarchy | 0% |
| | 6.4 Idle Core Scale & Opacity | `calculateCoreScale`, `calculateCoreOpacity` | Scale / opacity formulas | 0% |
| | 6.5 Speaking Audio-Reactive Core Expansion | `calculateCoreScale`, `calculateCoreOpacity` | Scale / opacity formulas | 0% |

### 4.2 Proof of Complete Independence
1. **Zero Imports of `resolveActiveState`**: `tests/test_challenger_m1_math_physics.ts` lines 13–34 import only `calculateBaseRingOpacity`, `calculateCardiacBeat`, `calculateCoreOpacity`, `calculateCoreScale`, `calculateRingSpeed`, `createDefaultStateWeights`, `StateTransitionPulseTracker`, and `updateStateWeights`. Neither `resolveActiveState` nor `normalizeStateName` is imported or referenced.
2. **Deterministic State Weights**: In all tests where state weights are used, weights are set directly (e.g. `w['ALERT'] = 1` or explicitly targeted by name `updateStateWeights(w, 'THINKING', dt)`). Tool resolution is never invoked.
3. **Execution Confirmation**: Running `npx tsx tests/test_challenger_m1_math_physics.ts` confirms 38/38 assertions PASS with VERDICT: CONFIRM.

### 4.3 Critical Implementation Constraint for Defensive Hardening
When Worker implements defensive hardening on `updateStateWeights` in `state-machine.ts`:
Line 144 currently reads:
```typescript
const dt = Math.min(0.05, delta)
```
In `tests/test_challenger_m1_math_physics.ts` line 392, the test explicitly evaluates sub-millisecond deltas:
```typescript
const testDts = [0.001, 0.00833, 0.01667, 0.03333, 0.05, 0.1, 1.0, 100.0]
for (const dt of testDts) {
  const w = createDefaultStateWeights()
  const { damp, dt: clampedDt } = updateStateWeights(w, 'THINKING', dt)
  const expectedDt = Math.min(0.05, dt)
...
  assert(
    Math.abs(clampedDt - expectedDt) < 1e-7 && Math.abs(damp - expectedDamp) < 1e-7,
...
```
**CRITICAL**: If the lower bound clamp were implemented as `Math.max(0.016, ...)` or `Math.max(0.005, ...)`, `clampedDt` for `dt = 0.001` would become `0.016` (or `0.005`), causing test 3.1 in Challenger 1 to fail!
Worker MUST use:
```typescript
const safeDelta = typeof delta === 'number' && Number.isFinite(delta) ? Math.max(0, delta) : 0.016
const dt = Math.min(0.05, safeDelta)
```
This safely clamps negative numbers to `0` and non-finite inputs (NaN/Inf) to `0.016`, while preserving exact values for any positive `delta <= 0.05`.

---

## 5. Review of Additional Required Fixes (D2 and Audio Bounds)

### 5.1 CustomEvent Object Detail Unpacking (Finding D2)
- **Target File**: `src/components/dashboard/holographic-core/holographic-core-scene.tsx`, lines 94–99.
- **Current Defect**:
  ```typescript
  const handleJarvisState = (e: Event) => {
    const customDetail = (e as CustomEvent).detail
    if (customDetail) {
      realtimeBusState.current = String(customDetail)
    }
  }
  ```
  `PROJECT.md` lines 61–62 specifies: `window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: HolographicState } }))`.
  When `{ detail: { state: 'ALERT' } }` is passed, `String(customDetail)` evaluates to `"[object Object]"`, which causes `normalizeStateName` to return `null`, ignoring the event.
- **Recommended Implementation**:
  ```typescript
  const handleJarvisState = (e: Event) => {
    const customDetail = (e as CustomEvent).detail
    if (customDetail) {
      const rawState =
        typeof customDetail === 'object' && customDetail !== null && 'state' in customDetail
          ? (customDetail as { state: unknown }).state
          : customDetail
      realtimeBusState.current = String(rawState)
    }
  }
  ```
  Also update line 113 to dispatch the compliant object format:
  ```typescript
  window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: mapped } }))
  ```

### 5.2 Audio Reactivity Bounds Clamping
- **Target File**: `src/components/dashboard/holographic-core/audio-bridge.ts`.
- **Hardening Items**:
  1. Safe delta clamping:
     ```typescript
     const safeDt = typeof dt === 'number' && Number.isFinite(dt) ? Math.max(0, Math.min(0.05, dt)) : 0.016
     const audioDamp = 1 - Math.exp(-14 * safeDt)
     ```
  2. Band output clamping:
     Clamp `rawBass`, `rawMid`, `rawTreble` to `[0, 1]` before and after exponential smoothing.

---

## 6. Exact Verification Test Plan for Worker and Reviewer 2

Worker and Reviewer 2 must execute the following 4-phase verification sequence in exact order:

### Phase 1: Math & Physics Regression Suite
```powershell
npx tsx tests/test_challenger_m1_math_physics.ts
```
- **Pass Criteria**:
  - Total Assertions: 38
  - Passed: 38
  - Failed: 0
  - Output ends with `VERDICT: CONFIRM` and exit code 0.

### Phase 2: Vitest Lifecycle & State Machine Suite
```powershell
npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
```
- **Pass Criteria**:
  - Test Files: 1 passed (1)
  - Tests: 24 passed (24)
  - Exit code 0.
  - Test 5 passes asserting `expect(actualState).toBe('DEEP_RESEARCH')`.

### Phase 3: TypeScript Compilation Typecheck
```powershell
npx tsc -p . --noEmit
```
- **Pass Criteria**:
  - Exit code 0.
  - Zero errors reported.

### Phase 4: Production Build Verification
```powershell
npx vite build
```
- **Pass Criteria**:
  - Exit code 0.
  - Production bundles successfully emitted in `dist/`.

### Reviewer 2 Checklist Matrix

| Target File | Verification Check | Acceptance Criterion |
|---|---|---|
| `state-machine.ts` lines 93–94 | Regex precedence order | `/research.../` checked before `/search.../` |
| `state-machine.ts` line 144 | Delta time lower clamping | `Math.max(0, delta)` (never `Math.max(0.016, delta)`) |
| `holographic-core-scene.tsx` line 94 | CustomEvent detail unpacking | Safely unpacks both `{ detail: { state: ... } }` and `{ detail: 'STATE' }` |
| `holographic-core-scene.tsx` line 113 | Keydown dispatch format | Dispatches `{ detail: { state: mapped } }` |
| `audio-bridge.ts` | Delta and band clamping | `safeDt` clamped to `[0, 0.05]`; frequency bands clamped to `[0, 1]` |
| `empirical-lifecycle.test.ts` line 184 | Test 5 alignment | Expects `'DEEP_RESEARCH'` for `gpt_researcher_query` |
