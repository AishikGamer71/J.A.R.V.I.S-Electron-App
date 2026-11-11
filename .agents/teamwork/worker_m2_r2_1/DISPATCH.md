## 2026-11-11T11:30:32Z
You are the Worker for Milestone 2 (Iteration 2 Remediation).
Working directory: e:\Projects\J.A.R.V.I.S Electron App
Your state folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m2_r2_1\

## MANDATORY INTEGRITY WARNING (VERBATIM)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Inputs & Context Files
- Original Request: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md
- Master Project Spec: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md
- Milestone 2 Scope: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m2_1\SCOPE.md
- Iteration 1 Gate Status: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m2_1\GATE_STATUS.md
- Reviewer 1 Report (FAIL): e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m2_1\review.md
- Challenger 1 Adversarial Report (REJECT): e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\challenger_m2_1\adversarial_report.md
- Challenger 1 Stress Harness: `tests/test_challenger_m2_adversarial_stress.ts`
- Explorer 1 Remediation Plan: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_1\report.md
- Explorer 2 Remediation Plan: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_2\report.md
- Explorer 3 Remediation Plan: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m2_r2_3\report.md

## Target Files You Own Exclusively
- `src/components/dashboard/holographic-core/state-machine.ts`
- `src/components/dashboard/holographic-core/holographic-core-scene.tsx`
- `src/lib/gateway-client.ts`
- `src/pages/dashboard.tsx`
- `src/components/dashboard/holographic-core/__tests__/empirical-lifecycle.test.ts`
- `src/components/dashboard/holographic-core/__tests__/event-wiring.test.ts`

## Specific Remediation Tasks (Follow Drop-in Blueprints in Explorer Reports)
1. **Remove `isLegacyTestFixture` in `state-machine.ts`**:
   - Completely delete `isLegacyTestFixture` lines 185–190. Level 4 priority `SPEAKING (80)` must unconditionally return `'SPEAKING'` when `props.isSpeaking`, `normalizedRealtime === 'SPEAKING'`, or `jarvisRealtimeRef.voiceState === 'SPEAKING'`.
   - Update `classifyToolState` with delimiter boundary regexes `(?:^|[_\W])` and `(?:[_\W]|$)` so generic tools like `credit_card_charge`, `adb_device`, `execute_workflow` don't collide with `CODING` or `MEMORY_SYNC`.

2. **Align Test Fixtures in `empirical-lifecycle.test.ts`**:
   - In lines 164–171, update the M1 test fixture to set `isSpeaking: false` so tool mapping is tested cleanly without contradictory `isSpeaking: true`.
   - Add explicit assertions verifying that when `isSpeaking: true` and `activeTool` are both passed, `SPEAKING (80)` properly preempts `activeTool`.

3. **Wire Arbitrator and Decay in `holographic-core-scene.tsx`**:
   - Instantiate `VisualizerStateArbitrator` and use it in `useFrame` to manage dwell and timeout lifecycle.
   - Add a decay timer (`busTimerRef`) in the `jarvis-state` / keydown listeners so transient states (`ALERT` 4000ms, tools 2000ms) automatically decay back to `null` (resting `IDLE`).
   - Ensure `jarvisRealtimeRef.voiceState === 'SPEAKING'` is never shadowed by stale `realtimeBusState.current`.

4. **Preserve Dwell & Timeout in `gateway-client.ts` and `dashboard.tsx`**:
   - In `gateway-client.ts` lines 287–291, do NOT immediately dispatch `jarvis-state: THINKING` with 0ms delay on `tool.result`. Delay by `TOOL_DWELL_MS` (2000ms).
   - In `gateway-client.ts` `playTtsAudio` cleanup, revert to post-speech active state instead of hardcoded `IDLE`.
   - In `dashboard.tsx` line 418, replace hardcoded `3000` with `TOOL_DWELL_MS` (2000ms) imported from `state-machine.ts`.

## Verification Commands (All Must Pass)
1. `npx tsx tests/test_challenger_m2_adversarial_stress.ts` — MUST pass 29/29 probes (VERDICT: APPROVE).
2. `npm run typecheck` — MUST pass with 0 errors across all 3 tsconfigs.
3. `npx vite build` — MUST pass with exit code 0.
4. `npx vitest run src/components/dashboard/holographic-core/__tests__/` — MUST pass 100%.

## Output Requirements
Write your detailed report to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m2_r2_1\report.md` and write a 5-component `handoff.md`.
Send a completion message to the orchestrator summarizing your implementation and test outputs.
