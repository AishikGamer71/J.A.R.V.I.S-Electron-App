# DISPATCH: reviewer_m1_1 (Code & Governance Reviewer)

## Identity
You are teamwork_reviewer (`reviewer_m1_1`).
Working directory: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m1_1`

## Task
You must read:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1\handoff.md`

Examine Milestone M1 work product:
1. Verify `backend/voice/assets/jarvis_ref.wav` exists, size is 353,708 bytes, SHA256 matches `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`.
2. Verify clean wipe of 24 legacy files and stubs, removal of `_safe_assets/`, and preservation of `native_core/jarvis_native_fallback.py`, `PROJECT.md`, `TEST_INFRA.md`.
3. Verify target 10 backend packages and `__init__.py` files.
4. Verify `.antigravity/rules.md` and `.agent/rules/rules.md` have identical SHA-256 hashes and contain Laws 1–4.
5. Verify 3 agent profiles, 3 memory profiles, and 6 runtime skill profiles exist with proper frontmatter and content.
6. Run verification commands:
   - `powershell -ExecutionPolicy Bypass -File scripts/verify-m1.ps1`
   - `python tests/e2e/runner.py --milestone M1`
   - `npm run typecheck`
7. Issue your structured review verdict: APPROVE or REQUEST_CHANGES.
8. Write `handoff.md` and send completion message to parent.

## 2026-11-10T08:53:34Z
Read e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m1_1\DISPATCH.md and follow all instructions strictly. Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m1_1. Write handoff.md with verdict (APPROVE or REQUEST_CHANGES) and send completion message to parent.
