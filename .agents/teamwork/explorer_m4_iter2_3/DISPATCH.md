# DISPATCH — explorer_m4_iter2_3 (MarkItDown Regex & Delimiter Robustness Explorer)

**Timestamp**: 2026-11-10T13:33:00Z
**Agent**: explorer_m4_iter2_3
**Role**: MarkItDown Regex & Delimiter Robustness Explorer
**Milestone**: M4 Iteration 2 Remediation

**Context & Failure Output to Address**:
In Milestone M4 Iteration 1 review:
- Finding 3 (reviewer_m4_2): `_repair_xlsx_xml` in `backend/automation/markitdown_service.py:347` uses `re.sub(r'showZeroes="0"', 'showZeroes="false"', text)`, which only catches double quotes and misses single quotes `showZeroes='0'` and spaced attributes `showZeroes = "0"`.
- Caveat 1 (challenger_m4_2): `repair_markdown_table` in `backend/automation/markitdown_service.py:207-227` strips the delimiter line when the input table already has a delimiter row at index 1 because delimiter insertion is guarded by `if not has_delimiter:`, and `start_idx = 2` skips index 1.

**Task**:
1. Investigate and design surgical fixes for `backend/automation/markitdown_service.py`:
   - Update `_repair_xlsx_xml` with regex: `re.sub(r'showZeroes\s*=\s*["\']0["\']', 'showZeroes="false"', text)` or similar robust pattern.
   - Update `repair_markdown_table` to unconditionally emit a clean normalized delimiter row `|---|---|` and preserve both un-delimited and pre-delimited markdown tables.
2. Produce a complete tested drop-in code blueprint for `backend/automation/markitdown_service.py`.
3. Deliver report in `.agents/teamwork/explorer_m4_iter2_3/handoff.md`.


## 2026-11-10T13:33:32Z
You are explorer_m4_iter2_3, the MarkItDown Regex & Delimiter Robustness Explorer for Milestone M4 Iteration 2 Remediation.
Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m4_iter2_3
Orchestrator Conversation ID: 0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4

MANDATORY FIRST STEP:
Read the following files before taking any action:
1. e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md
2. e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md
3. e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m4_iter2_3\DISPATCH.md
4. e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m4_2\handoff.md
5. e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\challenger_m4_2\handoff.md
6. Existing code: e:\Projects\J.A.R.V.I.S Electron App\backend\automation\markitdown_service.py

INVESTIGATION & REMEDIATION OBJECTIVE:
Two specific quality improvements were identified:
1. In `_repair_xlsx_xml` (`backend/automation/markitdown_service.py:347`):
   - Current: `re.sub(r'showZeroes="0"', 'showZeroes="false"', text)`
   - Misses single quotes (`showZeroes='0'`) and spaces (`showZeroes = "0"`).
   - Needs: `re.sub(r'showZeroes\s*=\s*["\']0["\']', 'showZeroes="false"', text)` or equivalent.
2. In `repair_markdown_table` (`backend/automation/markitdown_service.py:207-227`):
   - When input table already has a delimiter row (e.g. `| A | B |\n|---|---|\n| 1 | 2 |`), `has_delimiter` is True, but delimiter row is skipped if not handled carefully.
   - It should normalize and always emit a valid Markdown table with `|---|` delimiter row for both un-delimited and pre-delimited tables.
Your task:
1. Design surgical, robust fixes for both points.
2. Verify with test assertions:
   - `python -m unittest tests.e2e.test_tier1_features.TestTier1Milestone4Features.test_f28_04_table_repair`
3. Provide complete drop-in blueprints for the modified functions in `backend/automation/markitdown_service.py`.
4. Deliver report in `.agents/teamwork/explorer_m4_iter2_3/handoff.md` and notify parent via send_message.
