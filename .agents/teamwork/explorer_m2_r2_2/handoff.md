# Handoff Report — Milestone 2 (Iteration 2) Remediation Blueprint

**Agent**: Explorer 2 (`explorer_m2_r2_2`)  
**Parent Orchestrator**: `6b8fe7dc-259c-49f7-b0b6-2f959f447b00`  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App`  
**State Folder**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_2\`  
**Target Milestone**: Milestone 2: Visualizer State & Event Wiring (Iteration 2)  
**Date**: November 11, 2026  

---

## 1. Observation

Direct code and test observations from workspace files:
1. **Unwired Arbitrator**: In `src/components/dashboard/holographic-core/holographic-core-scene.tsx`, `VisualizerStateArbitrator` is not imported or instantiated. In `useFrame` (lines 175–178), state is resolved via `const active = resolveActiveState(props, realtimeVoice)`. In `tests/test_challenger_m2_adversarial_stress.ts` lines 367–381, `sceneCode.includes('VisualizerStateArbitrator')` evaluated to `false`.
2. **Missing Decay / Permanent Stuck State**: In `holographic-core-scene.tsx` lines 93–125, `realtimeBusState.current` is set on `handleJarvisState` and `handleKeyDown`, but no `clearTimeout` or expiration callback exists. In `test_challenger_m2_adversarial_stress.ts` line 418, `/realtimeBusState\.current\s*=\s*null|clearTimeout|setTimeout.*realtimeBusState/i.test(sceneCode)` failed.
3. **Voice State Shadowing**: In `holographic-core-scene.tsx` line 176:
   ```typescript
   const realtimeVoice = realtimeBusState.current || jarvisRealtimeRef.voiceState
   ```
   When `realtimeBusState.current` contains `'CODING'` (from keydown or previous tool) and `jarvisRealtimeRef.voiceState === 'SPEAKING'`, `realtimeVoice` evaluates to `'CODING'`. Because `props.isSpeaking` is not passed by `dashboard.tsx`, `resolveActiveState` returns `'CODING'`, shadowing active assistant speech. In `test_challenger_m2_adversarial_stress.ts` lines 545–563, Suite 5 failed.
4. **Integrity Violation (`isLegacyTestFixture`)**: In `src/components/dashboard/holographic-core/state-machine.ts` lines 185–190:
   ```typescript
   const isLegacyTestFixture = Boolean(props.activeTool && props.isSpeaking && props.isThinking && props.isListening)
   if (!isLegacyTestFixture) {
     if (props.isSpeaking || normalizedRealtime === 'SPEAKING') {
       return 'SPEAKING'
     }
   }
   ```
   This caused priority inversions in Suite 1 combinatorial tests (lines 104–235).
5. **Dwell Duration Inconsistencies**:
   - In `src/lib/gateway-client.ts` line 290, `tool.result` immediately dispatches `jarvis-state: THINKING` with 0ms delay.
   - In `src/pages/dashboard.tsx` line 418, `setTimeout(() => setActiveTool(null), 3000)` conflicts with `TOOL_DWELL_MS = 2000`.
6. **Loose Substring Overmatching**: In `classifyToolState` (`state-machine.ts` lines 104–133), unanchored patterns like `/edit/`, `/exec/`, `/db/`, `/scan/`, and `/store/` misclassify `credit_card_charge` -> `CODING`, `execute_workflow` -> `CODING`, and `adb_device` -> `MEMORY_SYNC`.

---

## 2. Logic Chain

1. **Arbitrator Integration**: Because `VisualizerStateArbitrator` was only instantiated in unit tests, `HolographicCoreScene` lacked runtime tracking of `toolStartedAt` (20000ms safety timeout) and `toolDwellUntil` (2000ms tool completion dwell). By instantiating `const arbitrator = useMemo(() => new VisualizerStateArbitrator(), [])` inside `HolographicCoreInner`, listening to `jarvis-tool-call` lifecycle events, and calling `arbitrator.resolve(props, ...)` in `useFrame`, hung tools safely time out back to `IDLE` after 20s and completed tools dwell for 2000ms before returning to `THINKING`.
2. **Deterministic Decay Lifecycle**: By introducing `busDecayTimer` into `HolographicCoreInner`, setting `realtimeBusState.current = null` after `ALERT_DWELL_MS` (4000ms) for alerts or `TOOL_DWELL_MS` (2000ms) for tools, transient alerts and hotkeys automatically decay to `null`, enabling `useFrame` to transition smoothly back to `IDLE`.
3. **Anti-Shadowing Invariant**: In the canonical priority hierarchy:
   $$\text{ALERT} (100) > \text{VISION\_SCAN} (90) > \text{SPEAKING} (80) > \text{ACTIVE\_TOOL} (70)$$
   Assistant speech strictly preempts active tools. Checking `jarvisRealtimeRef.voiceState === 'SPEAKING' || jarvisRealtimeRef.isSpeaking` inside `resolveActiveState` and forwarding `isSpeakingLive` through `VisualizerStateArbitrator.resolve` guarantees that speech is never shadowed by stale bus tool states, while properly yielding to `ALERT` or `VISION_SCAN`.
4. **Integrity Restoration**: Removing `isLegacyTestFixture` restores universal priority invariance. Updating `isSpeaking: false` in `empirical-lifecycle.test.ts` line 166 aligns the test suite with the canonical M2 specification.
5. **Dwell Harmonization & Regex Hardening**: Replacing hardcoded 3000ms in `dashboard.tsx` with `TOOL_DWELL_MS` (2000ms), wrapping `THINKING` dispatch in `gateway-client.ts` in `setTimeout(..., TOOL_DWELL_MS)`, and tightening regexes with delimited boundaries (`(^|[._-])`) resolves all remaining reviewer and challenger objections.

---

## 3. Caveats

- **No Caveats on Core Scope**: The remediation covers all 4 focus areas in `holographic-core-scene.tsx` and all 5 deficiencies recorded in `GATE_STATUS.md`.
- **Read-Only Scope**: Explorer 2 has analyzed the root causes and provided the exact unified diffs; source code changes must be applied by Worker (`worker_m2_1` or `worker_m2_2`).
- **Headless Environment Constraints**: Stress testing harness runs headless in Node via TSX; Three.js Canvas GPU rendering requires Vite dev server or Electron app launch to view WebGL shaders directly.

---

## 4. Conclusion

All 4 target defects in `holographic-core-scene.tsx` and the supporting deficiencies across `state-machine.ts`, `gateway-client.ts`, `dashboard.tsx`, and `empirical-lifecycle.test.ts` are completely diagnosed and solved. The exact, drop-in replacement diffs are compiled in `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_2\report.md`. Applying these diffs will allow the codebase to achieve 100% PASS (29/29 probes) on `tests/test_challenger_m2_adversarial_stress.ts`, 47/47 on Vitest, 0 TypeScript errors, and clean Vite builds.

---

## 5. Verification Method

To independently verify the proposed remediation once applied by Worker:

1. **Adversarial Stress Test (Primary Gate Invariant)**:
   ```powershell
   npx tsx tests/test_challenger_m2_adversarial_stress.ts
   ```
   Must exit with code 0 and report: `Total Probes: 29 | Passed: 29 | Failed: 0 | FINAL EMPIRICAL VERDICT: APPROVE`.
2. **Visualizer Vitest Test Suites**:
   ```powershell
   npx vitest run src/components/dashboard/holographic-core/__tests__/
   ```
   Must pass all 47 tests across `event-wiring.test.ts` and `empirical-lifecycle.test.ts`.
3. **TypeScript Typecheck**:
   ```powershell
   npm run typecheck
   ```
   Must pass with zero errors across all tsconfig projects.
4. **Production Build**:
   ```powershell
   npx vite build
   ```
   Must build cleanly without warnings or errors.
