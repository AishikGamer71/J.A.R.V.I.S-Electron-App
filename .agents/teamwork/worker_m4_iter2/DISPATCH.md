# DISPATCH — worker_m4_iter2 (Milestone M4 Iteration 2 Remediation Worker)

**Timestamp**: 2026-11-10T13:44:00Z
**Agent**: worker_m4_iter2
**Role**: Milestone M4 Iteration 2 Remediation Worker
**Milestone**: M4 Iteration 2 Remediation

**Assigned Tasks**:
Apply verified drop-in remediation blueprints across:
1. `backend/automation/browser_use_runner.py`:
   - Replace with the real Playwright/CDP implementation designed by `explorer_m4_iter2_1` (`.agents/teamwork/explorer_m4_iter2_1/proposed_browser_use_runner.py`).
   - Connect live Playwright Chromium (or Chrome/Edge channel) for `navigate`, `click`, `type`, `screenshot`, `extract_dom`, `extract_text`, `evaluate_js`.
   - Allow `about:blank` in `validate_url`.
   - Retain `MockCDPSession` strictly as a fallback.
2. `backend/core/tool_dispatcher.py`:
   - Replace lines 300–412 with the blueprint from `explorer_m4_iter2_2` (`.agents/teamwork/explorer_m4_iter2_2/handoff.md`).
   - Use `with BrowserUseRunner(...) as runner:` and defensive `try...finally: runner.close()` to eliminate process leaks.
3. `backend/automation/markitdown_service.py`:
   - Update `_repair_xlsx_xml` and `repair_markdown_table` using the blueprints from `explorer_m4_iter2_3` (`.agents/teamwork/explorer_m4_iter2_3/handoff.md`).
   - Regex: `re.sub(r'showZeroes\s*=\s*["\']\s*0\s*["\']', 'showZeroes="false"', text)`.
   - Table repair: unconditionally emit `|---|---|` delimiter row and preserve pre-delimited tables.
4. `tests/test_challenger_m4_2.py`:
   - In line 276, update expected lines from `2` to `3` to reflect the corrected table delimiter preservation.

**Mandatory References to Read**:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m4_2\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m4_iter2_1\handoff.md` and `proposed_browser_use_runner.py`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m4_iter2_2\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m4_iter2_3\handoff.md`

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

**Verification Required Before Handoff**:
1. `python tests/e2e/runner.py --milestone M4` (All 25 tests must pass)
2. `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone4Features`
3. `python -m unittest tests.e2e.test_tier2_boundaries.TestTier2DesktopAutomationBoundaries`
4. `python -m unittest tests.test_challenger_m4_2`
5. `python tests/e2e/runner.py --milestone all` (200 active tests must pass)
6. `git status --porcelain src/` (Verify exactly 0 lines of UI drift)

Deliver your report in `.agents/teamwork/worker_m4_iter2/handoff.md` and notify parent via send_message.

## 2026-11-10T13:54:57Z
**Context**: Milestone M4 Iteration 2 Remediation
**Content**: Safety timer check. Please report current status and progress on implementing browser_use_runner.py, tool_dispatcher.py, and markitdown_service.py.
**Action**: Update progress.md and respond with current status.
