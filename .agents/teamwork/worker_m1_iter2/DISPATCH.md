# DISPATCH: worker_m1_iter2 (Milestone M1 Iteration 2 Remediation)

## Identity & Role
You are teamwork_worker (`worker_m1_iter2`).
Working directory: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_iter2`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Inputs
You must read:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator\GATE_STATUS.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_iter2_1\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_iter2_2\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_iter2_3\handoff.md`

## Scope of Work (Iteration 2 Remediation)
You own and must modify exclusively these files:
1. `backend/main.py`:
   - Implement the complete FastAPI entrypoint scaffold per Section 2.2 of `explorer_m1_iter2_1\analysis.md`.
   - Provide `GET /health` returning `{"status": "healthy", "service": "jarvis-core-service", "version": "2.0.0"}`.
   - Provide `GET /api/system/stats`, `GET /v1/tools`, `POST /v1/tools/invoke`, and WebSockets `/ws` and `/ws/jarvis`.
2. `.antigravity/rules.md` and `.agent/rules/rules.md`:
   - Update with `ZERO UI DRIFT` and `DESKTOP APPLICATION ONLY` per `explorer_m1_iter2_2\handoff.md`.
   - Ensure both files match character-for-character with identical SHA-256 hash.
3. `backend/skills/desktop_assistant.md`:
   - Create alongside `desktop_control.md` per `explorer_m1_iter2_2\handoff.md`.
4. `src/components/widgets/arc-reactor.tsx` and `src/components/dashboard/sphere.tsx`:
   - Apply `Math.max(0, ...)` lower bound to delta time calculation.
   - Ensure zero other UI files are touched.

## Mandatory Verification Requirements
You MUST run the following commands and include full command outputs in your `handoff.md`:
1. `python tests/e2e/runner.py --tier 1` (Verify Milestone M1 passes 30/30 with 0 failures).
2. `python tests/e2e/runner.py --milestone M1` (Verify 0 failures, 0 errors).
3. `python tests/test_m1_adversarial.py` (Verify 8/8 pass with clause checks True).
4. `powershell -ExecutionPolicy Bypass -File scripts/verify-m1.ps1` (Verify all checks pass).
5. `npm run typecheck` (Verify exit code 0).

Write your report to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_iter2\handoff.md` and notify parent.

## 2026-11-10T09:12:47Z
Read e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_iter2\DISPATCH.md and follow all instructions strictly. Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1_iter2. Implement the 4 remediation items, run all verification commands, write handoff.md, and send completion message to parent.
