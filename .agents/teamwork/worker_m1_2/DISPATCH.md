# Worker Task Assignment: Iteration 2 Remediation & Hardening

Working directory: e:\Projects\J.A.R.V.I.S Electron App
State folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_2\

## Mandatory Inputs (Read these first)
- Original Request: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Project Specification: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md`
- Sub-Orchestrator Scope: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m1_1\SCOPE.md`
- Explorer Iteration 2 Reports:
  - `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_fix_1\report.md`
  - `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_event_1\report.md`
  - `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_tests_1\report.md`
- Reviewer 2 Handoff: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m1_contracts_1\handoff.md`
- Files to modify:
  - `src/components/dashboard/holographic-core/state-machine.ts`
  - `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
  - `src/components/dashboard/holographic-core/audio-bridge.ts`
  - `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`

## MANDATORY INTEGRITY WARNING (Verbatim)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You exclusively own and may modify:
- `src/components/dashboard/holographic-core/state-machine.ts`
- `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
- `src/components/dashboard/holographic-core/audio-bridge.ts`
- `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
- `src/components/dashboard/sphere.tsx` (if needed)

## Your Task
Apply the verified remediation plan from the Iteration 2 Explorer reports:
1. `src/components/dashboard/holographic-core/state-machine.ts`:
   - In `resolveActiveState` (lines 91-99), evaluate `/research|delegate|analyze|investigate/i` BEFORE `/search|browse|crawl|google|web/i`.
   - In `updateStateWeights` (line 144), add finite & non-negative lower bound clamping:
     `const safeDt = Number.isFinite(delta) ? Math.max(0, Math.min(0.05, delta)) : 0`
2. `src/components/dashboard/holographic-core/holographic-core-scene.tsx`:
   - In `handleJarvisState` (lines 94-98), implement safe object unpacking:
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
3. `src/components/dashboard/holographic-core/audio-bridge.ts`:
   - Clamp external audio level to `[0, 1]`:
     `const externalLevel = Number.isFinite(rawExternal) ? Math.min(1.0, Math.max(0, rawExternal)) : 0`
4. `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`:
   - Update the defect reproduction test at line 184 to assert `expect(actualState).toBe('DEEP_RESEARCH')` now that the fix is in place.
   - Add test case verifying object payload unpacking `{ detail: { state: 'THINKING' } }`.
5. Run the full verification suite:
   - `npx vitest run src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
   - `npx tsx tests/test_challenger_m1_math_physics.ts`
   - `npx tsc -p . --noEmit`
   - `npx vite build`

Document all commands and results in `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_2\handoff.md` and send a message when complete.


## 2026-11-11T10:02:53Z
You are the Worker agent responsible for applying targeted remediation and hardening for Milestone 1 Iteration 2.

Working directory: e:\Projects\J.A.R.V.I.S Electron App
Your state folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_2\
