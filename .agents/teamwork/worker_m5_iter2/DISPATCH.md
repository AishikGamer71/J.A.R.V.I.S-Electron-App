# Task Assignment: Milestone M5 Iteration 2 Worker

## 2026-11-10T16:10:00Z

**Agent**: `worker_m5_iter2`
**Role**: Milestone M5 Iteration 2 Worker
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m5_iter2\`
**Parent Orchestrator ID**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`
**Reference Documents**:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md` (MANDATORY: Subagents MUST read it before starting work)
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\orchestrator\GATE_STATUS.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m5_iter2_1\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m5_iter2_2\handoff.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m5_iter2_3\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You have exclusive write ownership of:
1. `backend/main.py`
2. `backend/memory/hybrid_rag.py`
3. `backend/senses/crawl4ai_service.py`
4. `backend/senses/mobilerun_service.py`
5. `backend/senses/deepface_sentry.py`
6. `tests/e2e/test_tier1_features.py`

DO NOT touch any file in `src/` (ZERO UI DRIFT invariant).
DO NOT touch any other backend files unless strictly necessary for imports/signatures.

## Implementation Tasks

### 1. `backend/main.py`
- **Line 430 (`/search`)**: Change `hybrid_results = hybrid_memory.search(q, limit=10)` to `hybrid_results = hybrid_memory.search(q, top_k=10)`.
- **Lines 485–497 (`/v1/permissions`)**: Safely extract tool names from OpenAPI/OpenAI function schemas returned by `tool_dispatcher.get_tool_definitions()`:
  ```python
  perms: Dict[str, Any] = {}
  for t in tools:
      if not isinstance(t, dict):
          continue
      tool_name = t.get("name") or t.get("function", {}).get("name")
      if tool_name:
          perms[tool_name] = {
              "scope": "*",
              "granted": True,
              "risk_level": t.get("risk_level") or t.get("function", {}).get("risk_level", "LOW"),
          }
  return {"permissions": perms}
  ```

### 2. `backend/memory/hybrid_rag.py`
- In `search()` (line 332): add optional parameter `limit: Optional[int] = None`. If `limit is not None: top_k = limit`.

### 3. `backend/senses/crawl4ai_service.py`
- In `_regex_html_to_markdown(self, html: str)`:
  - If `self.filter_noise`: strip cookie/banner/popup/modal/newsletter container classes via:
    `text = re.sub(r"<[a-z0-9]+[^>]*class=[\"'][^\"']*(?:cookie|banner|advert|popup|modal|newsletter)[^\"']*[\"'][^>]*>[\s\S]*?</[a-z0-9]+>", "", text, flags=re.I)`
  - Handle unclosed headings and paragraphs using lookahead: `(?:</h1|(?=<[a-z/!]|\n|$))`

### 4. `backend/senses/mobilerun_service.py`
- In `validate_adb_command(self, cmd: str)`:
  - Add `or not cmd.strip()` to reject whitespace-only commands immediately (`return False`).
  - Update `DANGEROUS_COMMAND_PATTERNS` regex at line 20 to:
    `r"\brm\s+(?:-[a-zA-Z0-9-]+\s+)*[\"']?(?:\/|\/system|\/data|\/boot|\/sdcard)"`
  - Add token-based inspection of `clean.split()` to block split flags like `rm -r -f /system` or `rm -f -r /data`.

### 5. `backend/senses/deepface_sentry.py`
- In `_authenticate_mock` (lines 193–212):
  - On owner match: reset `self._stranger_streak = 0`.
  - On non-match: delegate to `return self._record_stranger("Face embedding did not match registered owner")` so that `_stranger_streak` increments and triggers `"STRANGER_SENTRY_ALERT"` on the 3rd attempt.

### 6. `tests/e2e/test_tier1_features.py`
- Append `test_f35_06_search_endpoint_contract`, `test_f35_07_permissions_endpoint_contract`, and `test_f35_08_health_endpoint_response` to `TestTier1Features` exercising actual HTTP requests via `TestClient(app)`.

## Required Verification Commands
Execute the following verification suites and include complete outputs in `handoff.md`:
1. `python -m unittest tests.test_challenger_m5_gateway_ws` (verify 19/19 pass)
2. `python -m unittest tests.test_adversarial_m5_vision_mobile` (verify 31/31 pass)
3. `python -m unittest discover -s tests/e2e -p "test_tier1_features.py"` (verify 203/203 pass)
4. `python tests/e2e/runner.py --milestone M5` (verify 50/50 pass)
5. `python tests/e2e/runner.py` (verify 250/250 pass)
6. `git status --porcelain src/` (verify 0 lines UI drift)

Output your report to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m5_iter2\handoff.md`.
