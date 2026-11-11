# Explorer Task Assignment: Fix Strategy for Active Tool Regex & Bounds Clamping (Iteration 2)

Working directory: e:\Projects\J.A.R.V.I.S Electron App
State folder: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_fix_1\

## Mandatory Inputs (Read these first)
- Original Request: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Project Specification: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator_1\PROJECT.md`
- Sub-Orchestrator Scope: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m1_1\SCOPE.md`
- Reviewer 2 Handoff (Failure Feedback): `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m1_contracts_1\handoff.md`
- Challenger 1 Handoff (Hardening Recommendations): `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\challenger_m1_math_1\handoff.md`
- Implementation File: `src/components/dashboard/holographic-core/state-machine.ts`

## Reviewer 2 Feedback (Defect D1)
In `src/components/dashboard/holographic-core/state-machine.ts` lines 93-94:
```typescript
if (/search|browse|crawl|google|web/i.test(tool)) return 'WEB_SEARCH'
if (/research|delegate|analyze|investigate/i.test(tool)) return 'DEEP_RESEARCH'
```
Because `"researcher"` contains `"search"`, `gpt_researcher_*` maps to `WEB_SEARCH` instead of `DEEP_RESEARCH`.
Fix required: evaluate `DEEP_RESEARCH` before `WEB_SEARCH`.
Also check Challenger 1's hardening: `const safeDt = Math.max(0, Math.min(0.05, delta))` in `updateStateWeights`.

## Your Task
Analyze the exact changes needed in `state-machine.ts` to satisfy Reviewer 2 and Challenger 1, ensuring all vitest tests in `empirical-lifecycle.test.ts` pass cleanly.
Write your recommendations to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_r2_fix_1\report.md` and deliver `handoff.md`.
