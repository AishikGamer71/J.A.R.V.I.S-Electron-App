# Review Report & Handoff: Interface Conformance & Dashboard Integration (Milestone 1)

**Agent**: Reviewer 2 (`reviewer_m1_contracts_1`)  
**Roles**: Reviewer, Adversarial Critic  
**Parent Orchestrator**: `b204d4ed-af14-4d46-bc7b-8d5d589f3895`  
**Date**: November 11, 2026  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Typecheck and Build Commands
- **TypeScript Typecheck**:
  Command: `npx tsc -p . --noEmit`
  Result: Exited with code 0. Zero errors.
  Full workspace typecheck: `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`).
  Result: Exited with code 0. Zero errors.
- **Production Vite Build**:
  Command: `npx vite build`
  Result: Exited with code 0. `✓ built in 4.67s` (`dist/assets/index-DhzkO0Vd.js 3,357.64 kB`).
- **Vitest Suite**:
  Command: `npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
  Result: Exited with code 1. 20 passed, 3 failed.
  Verbatim failure output:
  ```
  FAIL ui src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts > Empirical Verification: Holographic Core Lifecycle & State Machine > Area 1: 11-State Priority Arbitration (6-Level Hierarchy) > Level 3: activeTool maps tools to 6 distinct canonical states
  AssertionError: expected 'WEB_SEARCH' to be 'DEEP_RESEARCH' // Object.is equality

  Expected: "DEEP_RESEARCH"
  Received: "WEB_SEARCH"

   ❯ src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts:164:43
      162| isListening: true,
      163| }
      164| expect(resolveActiveState(props)).toBe(expected)
         | ^
  ```

### 1.2 Interface Conformance & Exports Inspection
In `src/components/dashboard/sphere.tsx`:
- Line 28: `export const Sphere = React.memo(SphereComponent, ...)`
- Line 45: `export default Sphere`
- Line 6: `export * from './holographic-core/types'` (exports `HolographicState`, `JarvisVisualState`, `SphereProps`, `ParticleSphereProps`)
- Line 7-12: Re-exports all constants, textures, geometries, state-machine, audio-bridge, and scene components.
In `src/pages/dashboard.tsx`:
- Line 6: `import Sphere from '@/components/dashboard/sphere'`
- Line 606: `<Sphere />` (rendered without props in fullscreen overlay)
- Line 695: `<Sphere />` (rendered without props in standard telemetry dashboard)

### 1.3 Active Tool Arbitration Flaw
In `src/components/dashboard/holographic-core/state-machine.ts`:
```typescript
91:  if (props.activeTool && typeof props.activeTool === 'string' && props.activeTool.trim() !== '') {
92:    const tool = props.activeTool.toLowerCase()
93:    if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
94:    if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
95:    if (/code|terminal|bash|edit|exec|shell/i.test(tool)) return 'CODING'
96:    if (/vision|camera|scan|face|lidar/i.test(tool)) return 'VISION_SCAN'
97:    if (/memory|db|store|sync|recall/i.test(tool)) return 'MEMORY_SYNC'
98:    return 'EXECUTING_TOOL'
99:  }
```
Observation: The tool string `'gpt_researcher_query'` matches `/search|browse|crawl|google|web/i` on line 93 because the substring `'search'` is contained inside `'researcher'`. Line 94 is never reached.

### 1.4 CustomEvent Detail Structure
In `src/components/dashboard/holographic-core/holographic-core-scene.tsx`:
```typescript
94:    const handleJarvisState = (e: Event) => {
95:      const customDetail = (e as CustomEvent).detail
96:      if (customDetail) {
97:        realtimeBusState.current = String(customDetail)
98:      }
99:    }
```
In `orchestrator_1/PROJECT.md` line 62:
```typescript
window.dispatchEvent(new CustomEvent('jarvis-state', { detail: { state: HolographicState } }));
```
Observation: If `detail` is `{ state: 'THINKING' }`, `String(customDetail)` produces `"[object Object]"`, failing state normalization.

### 1.5 Forensic Integrity Audit
- No hardcoded test result lookups or expected outputs were found in production source files.
- Fibonacci particle geometry is generated analytically using golden ratio $\pi(3-\sqrt{5})$.
- Exponential damping uses frame-rate independent continuous physics ($1 - \exp(-6.2 \cdot dt)$).
- Audio reactivity samples real Web Audio `AnalyserNode` frequency bins with 3-band partitioning.
- Integrity Violation Check: **PASS (Zero integrity violations found)**.

---

## 2. Logic Chain

1. **Interface Contract Verification (PASS)**:
   - Observation 1.2 confirms `src/components/dashboard/sphere.tsx` provides both named export `export const Sphere` and default export `export default Sphere`.
   - It re-exports all canonical and backward-compatible types (`HolographicState`, `JarvisVisualState`, `SphereProps`, `ParticleSphereProps`).
   - `src/pages/dashboard.tsx` imports `Sphere` and invokes `<Sphere />` without props at lines 606 and 695. Both invocations compile cleanly and resolve to default `IDLE` state with 2600 particles and standard dimensions.

2. **Backward Compatibility & Type Safety (PASS)**:
   - Observations 1.1 and 1.2 demonstrate that `dashboard.tsx` and all consumers compile cleanly without modification under `tsc -p . --noEmit` and `npm run typecheck`.
   - Production bundle completes in 4.67s via `npx vite build` without syntax or bundling errors.
   - Props arbitration correctly handles legacy boolean flags (`isSpeaking` > `isThinking` > `isListening`), error objects (`error` -> `ALERT`), and explicit overrides (`overrideState` / `state`).

3. **Arbitration Defect Identification (FAIL - Finding 1)**:
   - In Observation 1.3, `state-machine.ts` checks `/search|browse|crawl|google|web/i` before `/research|delegate|analyze|investigate/i`.
   - Because English word `"researcher"` contains the substring `"search"`, any tool starting with or containing `researcher` (specifically `gpt_researcher_*` specified in `PROJECT.md` line 68) matches the `WEB_SEARCH` branch prematurely.
   - This causes an explicit regression where `gpt_researcher` maps to `WEB_SEARCH` instead of `DEEP_RESEARCH`, causing test failure in `empirical-lifecycle.test.ts:164`.

4. **Event Bus Detail Handling (Finding 2)**:
   - In Observation 1.4, `holographic-core-scene.tsx` casts `customDetail` directly with `String(customDetail)`.
   - While existing legacy code (`gateway-client.ts`, `hermes-adapter.ts`) dispatches string literals, `PROJECT.md` specifies dispatching `{ detail: { state: HolographicState } }`. If an object payload is dispatched, it resolves to `"[object Object]"`.

5. **Test Assertion Invalidation (Analysis of Failures 2 & 3)**:
   - In Three.js, `THREE.Texture.prototype.needsUpdate` is a write-only setter (`set needsUpdate(value) { if (value) this.version++; }`). Reading `glowTex.needsUpdate` returns `undefined`.
   - The test assertions in `empirical-lifecycle.test.ts:514` and `524` expecting `needsUpdate === true` are invalid test assertions; `procedural-textures.ts` correctly sets `texture.needsUpdate = true` which increments `texture.version` to 1.

---

## 3. Findings

### [Major] Finding 1: Regex Precedence Flaw in `activeTool` State Arbitration
- **What**: Tool names containing `"researcher"` (e.g., `gpt_researcher_query`) resolve to `WEB_SEARCH` instead of `DEEP_RESEARCH`.
- **Where**: `src/components/dashboard/holographic-core/state-machine.ts:93-94`
- **Why**: The regex `/search|browse|crawl|google|web/i` on line 93 matches the substring `"search"` in `"researcher"` before the `/research/` check on line 94 can be evaluated. This violates specification `PROJECT.md` line 68 (`gpt_researcher_* -> DEEP_RESEARCH`).
- **Suggestion**: Invert the evaluation order or use bounded regex patterns. Testing `DEEP_RESEARCH` tools before `WEB_SEARCH` tools eliminates the conflict:
  ```typescript
  // Check DEEP_RESEARCH before WEB_SEARCH so 'researcher' is not swallowed by 'search'
  if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
  if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
  ```

### [Minor] Finding 2: `handleJarvisState` Does Not Support Object Payloads
- **What**: `window.addEventListener('jarvis-state')` assumes `e.detail` is a string primitive.
- **Where**: `src/components/dashboard/holographic-core/holographic-core-scene.tsx:94-98`
- **Why**: `PROJECT.md` line 62 documents `new CustomEvent('jarvis-state', { detail: { state: HolographicState } })`. Passing an object causes `String(customDetail)` to evaluate to `"[object Object]"`, failing normalization.
- **Suggestion**: Safely unpack object payloads:
  ```typescript
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

### [Minor / Informational] Finding 3: Dashboard Container Has `pointer-events-none`
- **What**: The outer wrapper in `src/pages/dashboard.tsx` has `pointer-events-none`.
- **Where**: `src/pages/dashboard.tsx:605, 693`
- **Why**: Pointer orbit drag events cannot reach the Canvas element unless the parent container enables pointer events or `<Sphere className="pointer-events-auto" />` is passed. This is inherited from legacy code, but should be noted for UI interactive testing.

---

## 4. Adversarial Challenge & Stress Tests

| Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| `<Sphere />` with 0 props | Defaults to IDLE, 2600 particles, w-full h-full | Defaults to IDLE, renders without error | **PASS** |
| Legacy flags: `isSpeaking=true`, `isThinking=true`, `isListening=true` | Speaking takes precedence over thinking and listening | Resolves to SPEAKING | **PASS** |
| Error prop: `error="DB crash"` with `isSpeaking=true` | Error takes precedence over legacy booleans | Resolves to ALERT | **PASS** |
| Explicit prop: `overrideState="CODING"` with `error="fail"` | Explicit override takes precedence over error | Resolves to CODING | **PASS** |
| Tool mapping: `activeTool="gpt_researcher_query"` | Resolves to DEEP_RESEARCH | Resolves to WEB_SEARCH | **FAIL (Finding 1)** |
| Tool mapping: `activeTool="crawl4ai_extract"` | Resolves to WEB_SEARCH | Resolves to WEB_SEARCH | **PASS** |
| Tool mapping: `activeTool="code_executor"` | Resolves to CODING | Resolves to CODING | **PASS** |
| Tool mapping: `activeTool="camera_stream"` | Resolves to VISION_SCAN | Resolves to VISION_SCAN | **PASS** |
| Tool mapping: `activeTool="memory_checkpoint"` | Resolves to MEMORY_SYNC | Resolves to MEMORY_SYNC | **PASS** |
| Tool mapping: `activeTool="random_unknown_tool"` | Resolves to EXECUTING_TOOL | Resolves to EXECUTING_TOOL | **PASS** |
| Invalid state: `state="INVALID_XYZ"` with `isListening=true` | Falls through invalid explicit state to Level 4 | Resolves to LISTENING | **PASS** |
| Audio bridge: `audioLevel=NaN` or negative | Handled gracefully without propagating NaN | Bands remain finite; fallback active | **PASS** |
| Audio bridge: Quiescent audio in SPEAKING | Autonomous multi-harmonic cadence simulation | Activates autonomous speech simulation | **PASS** |
| Orbit drag pitch angle | Clamped within $[-1.05, +1.05]$ radians ($\pm 60^\circ$) | Strictly clamped | **PASS** |

---

## 5. Caveats

- Milestone 2 will wire backend WebSockets (`/ws` and `/ws/jarvis`) and live gateway clients to the event bus; this review focused exclusively on component-level contracts, arbitration logic, and backward compatibility for Milestone 1.

---

## 6. Conclusion

The core architecture, 4-layer optical rendering, procedural textures, Three.js scene graph, type definitions, and backward compatibility with `dashboard.tsx` are extraordinarily high quality and compile with zero errors under both `tsc -p . --noEmit` and `npx vite build`.

However, because of the regex evaluation order defect in `state-machine.ts` (where `gpt_researcher` is classified as `WEB_SEARCH` instead of `DEEP_RESEARCH`), the arbitration engine fails specification compliance for `activeTool` resolution.

Per reviewer and critic integrity rules, the verdict is **REQUEST_CHANGES**.

---

## 7. Verification Method

To verify the required fix:

1. Update `src/components/dashboard/holographic-core/state-machine.ts` lines 93-94 to evaluate `DEEP_RESEARCH` regex before `WEB_SEARCH`.
2. Run vitest:
   ```powershell
   npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts
   ```
   *Verification condition*: `Level 3: activeTool maps tools to 6 distinct canonical states` must pass.
3. Verify typecheck and build:
   ```powershell
   npx tsc -p . --noEmit
   npx vite build
   ```
   *Verification condition*: Both exit with code 0.
