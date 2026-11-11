# Review & Adversarial Challenge Report — Milestone M5: Unified Gateway, Lifecycle & Multi-Env

**Reviewer Agent**: `reviewer_m5_2`  
**Role**: Objective Reviewer & Adversarial Critic  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\reviewer_m5_2`  
**Date**: 2026-11-10T15:56:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Direct Test Suite Execution Facts
All standard unittest and runner suites were executed directly from workspace terminal:

1. **Tier 1 Feature Tests**:
   - Command: `python -m unittest tests.e2e.test_tier1_features`
   - Verbatim Output:
     ```
     Ran 200 tests in 5.303s
     OK
     ```

2. **Tier 2 Boundary Tests**:
   - Command: `python -m unittest tests.e2e.test_tier2_boundaries`
   - Verbatim Output:
     ```
     Ran 47 tests in 0.005s
     OK
     ```

3. **Tier 3 Combination Tests**:
   - Command: `python -m unittest tests.e2e.test_tier3_combinations`
   - Verbatim Output:
     ```
     Ran 8 tests in 0.000s
     OK
     ```

4. **Tier 4 Scenario Tests**:
   - Command: `python -m unittest tests.e2e.test_tier4_scenarios`
   - Verbatim Output:
     ```
     Ran 5 tests in 0.000s
     OK
     ```

5. **Milestone M5 Unified Runner**:
   - Command: `python tests/e2e/runner.py --milestone M5`
   - Verbatim Output:
     ```
     ======================================================================
      J.A.R.V.I.S. UNIFIED E2E TEST RUNNER
      Target Tier: all | Target Milestone: M5
     ======================================================================
      Execution completed in 3.401s
      Total Tests Run : 50
      Passed           : 50
      Skipped (Pending): 0
      Failed           : 0
      Errors           : 0
     ======================================================================
      RESULT: SUCCESS (All active requirements satisfied)
     ======================================================================
     ```

6. **Full Test Suite Unified Runner**:
   - Command: `python tests/e2e/runner.py`
   - Verbatim Output: `Total Tests Run: 250, Passed: 250, Skipped: 0, Failed: 0, Errors: 0, RESULT: SUCCESS`.

7. **UI Immutability Audit**:
   - Command: `git status --porcelain src/`
   - Verbatim Output:
     ```
      M src/components/dashboard/sphere.tsx
     ?? src/components/widgets/arc-reactor.tsx
     ```
     Confirmed zero UI drift outside approved Milestone M1 files.

8. **21 Core Module Imports**:
   - Command: `python -c "modules = ['backend.core.hermes_brain', 'backend.engine.model_router', 'backend.memory.state_db', 'backend.memory.hybrid_rag', 'backend.memory.instinct_engine', 'backend.security.agent_shield', 'backend.voice.wakeword_engine', 'backend.voice.realtime_stt', 'backend.voice.omnivoice_service', 'backend.automation.windows_mcp_bridge', 'backend.automation.omniparser_service', 'backend.automation.agent_s3_runner', 'backend.automation.browser_use_runner', 'backend.automation.markitdown_service', 'backend.senses.camera_hub', 'backend.senses.deepface_sentry', 'backend.senses.mediapipe_gestures', 'backend.senses.crawl4ai_service', 'backend.senses.gpt_researcher_service', 'backend.senses.mobilerun_service', 'backend.hardware.power_guardian']; [__import__(m) for m in modules]; print('ALL 21 IMPORTED SUCCESSFULLY')"`
   - Verbatim Output: `ALL 21 IMPORTED SUCCESSFULLY`.

---

### 1.2 Adversarial Verification Findings (Critical Defect Observations)

When exercising the REST endpoints on `backend/main.py` using `fastapi.testclient.TestClient`, two critical runtime exceptions were discovered:

#### Finding 1: `GET /search` Crashes with TypeError (HTTP 500)
- **Location**: `backend/main.py`, line 430
- **Code**:
  ```python
  @app.get("/search")
  async def search(q: str = Query("")) -> Dict[str, Any]:
      fts_results = state_db.search_fts(q, limit=20)
      hybrid_results = hybrid_memory.search(q, limit=10)
      return {"query": q, "results": fts_results, "hybrid_hits": hybrid_results}
  ```
- **Observation / Verbatim Traceback**:
  ```python
    File "backend/main.py", line 430, in search
      hybrid_results = hybrid_memory.search(q, limit=10)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  TypeError: HybridMemory.search() got an unexpected keyword argument 'limit'
  ```
- **Root Cause**: In `backend/memory/hybrid_rag.py`, line 332:
  ```python
  def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[SearchResult]:
  ```
  The signature accepts `top_k`, NOT `limit`.
- **Impact**: Any client calling `GET /search?q=...` receives a 500 Internal Server Error (`{"status": "error", "message": "HybridMemory.search() got an unexpected keyword argument 'limit'", "code": "INTERNAL_GATEWAY_ERROR"}`).

#### Finding 2: `GET /v1/permissions` Crashes with KeyError (HTTP 500)
- **Location**: `backend/main.py`, lines 485–496
- **Code**:
  ```python
  @app.get("/v1/permissions")
  async def get_permissions() -> Dict[str, Any]:
      tools = tool_dispatcher.get_tool_definitions()
      perms = {
          t["name"]: {
              "scope": "*",
              "granted": True,
              "risk_level": t.get("risk_level", "LOW"),
          }
          for t in tools
      }
      return {"permissions": perms}
  ```
- **Observation / Verbatim Traceback**:
  ```python
    File "backend/main.py", line 489, in <dictcomp>
      t["name"]: {
      ~^^^^^^^^
  KeyError: 'name'
  ```
- **Root Cause**: `tool_dispatcher.get_tool_definitions()` returns OpenAI function-calling tool objects:
  ```json
  {"type": "function", "function": {"name": "echo", "description": "...", "parameters": {...}}}
  ```
  Top-level dictionary key `"name"` does not exist. It is nested under `t["function"]["name"]`.
- **Impact**: Any client calling `GET /v1/permissions` receives a 500 Internal Server Error (`{"status": "error", "message": "'name'", "code": "INTERNAL_GATEWAY_ERROR"}`).

#### Finding 3: Test Suite Verification Gap (Shallow Route Assertions)
- **Location**: `tests/e2e/test_tier1_features.py`, lines 1074–1088
- **Code**:
  ```python
  def test_f35_03_health_endpoint_contract(self):
      from backend.main import app
      routes = [r.path for r in app.routes]
      self.assertIn("/health", routes)
  ```
- **Observation**: Features #35 (REST Gateway) and #36 (WebSocket Gateway) were only tested by checking route string containment in `app.routes`. No HTTP requests were dispatched to `/search`, `/v1/permissions`, or other endpoints, allowing broken endpoints to slip through the 250/250 passing test suite without triggering a test failure.

---

## 2. Logic Chain

1. **Requirement Contract Analysis**:
   - `ORIGINAL_REQUEST.md § R4` and `PROJECT.md § Feature 35` mandate a Unified REST Gateway on `127.0.0.1:8765` providing working endpoints for `/search`, `/v1/permissions`, `/v1/tools`, etc.
   - The Gateway is the sole entry point for the Electron frontend and desktop clients.

2. **Deduction from Observations**:
   - While `backend/main.py` successfully mounts routes and declares schemas, live invocation of `GET /search` and `GET /v1/permissions` triggers uncaught exceptions (`TypeError` and `KeyError`).
   - The test assertions in `tests/e2e/test_tier1_features.py` for Feature 35 only evaluated route registration (`[r.path for r in app.routes]`) rather than executing actual requests with `TestClient`.
   - Consequently, the existing tests reported a 100% pass rate despite the presence of production-blocking HTTP 500 errors.

3. **Subsystem Assessment**:
   - `scripts/setup-environments.ps1`: AST syntax verified valid. Parameter handling (`-Force`, `-SkipVerify`, `-PythonVersion`) and exit codes (`exit 0` / `exit 1`) are properly implemented.
   - `docs/UNIFIED_ARCHITECTURE.md`: Accurately covers the tri-port model (8765, 8001, 8002), `AgentShield`, and all 17 open-source repos.
   - `README.md`: Comprehensively documents installation, setup, multi-env configuration, and testing.
   - Lifespan context manager: Cleanly starts `power_guardian`, `telemetry_store`, and `cron_scheduler`, and cleanly shuts them down.
   - WebSockets: Full-duplex `/ws` and `/ws/jarvis` routes properly handle command envelopes (`system.toggle`, `vision.mode`, `audio.control`, `reset_abort`), malformed JSON payloads, and streaming turns from `hermes_brain`.

---

## 3. Caveats

1. **No Implementation Changes Made**:
   - In strict compliance with the reviewer role constraint ("Review-only — do NOT modify implementation code"), no edits were made to `backend/main.py` or the test suite.
2. **Intentional Fallback Logic**:
   - Hardware-dependent modules (`CameraHub`, `DeepFaceSentry`, `MediaPipeGestures`, `MobileRunService`) correctly implement mock/synthetic fallbacks for headless CI environments. This is by design and does not constitute an integrity violation.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M5 is functionally close to completion (architecture docs, PowerShell automation, WebSockets, lifespan management, and 21 module imports are all solid). However, work cannot be approved until the two critical endpoint defects and the corresponding test coverage gap are resolved:

### Required Action Items for Worker M5:
1. **Fix `backend/main.py:430`**:
   Change `hybrid_results = hybrid_memory.search(q, limit=10)` to:
   ```python
   hybrid_results = hybrid_memory.search(q, top_k=10)
   ```
2. **Fix `backend/main.py:488`**:
   Safely extract tool names from OpenAI schemas:
   ```python
   perms = {}
   for t in tools:
       name = t.get("name") or t.get("function", {}).get("name", "unknown")
       perms[name] = {
           "scope": "*",
           "granted": True,
           "risk_level": t.get("risk_level") or t.get("function", {}).get("risk_level", "LOW"),
       }
   ```
3. **Harden Tier 1 & Tier 2 Tests**:
   Update `tests/e2e/test_tier1_features.py` (Feature 35) to perform actual HTTP GET/POST calls using `fastapi.testclient.TestClient` against `/health`, `/api/system/stats`, `/search?q=test`, `/v1/tools`, and `/v1/permissions`.

---

## 5. Verification Method

To verify the required fixes once implemented:

1. **Verify `/search` and `/v1/permissions` via TestClient**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app); r1 = c.get('/search?q=jarvis'); r2 = c.get('/v1/permissions'); assert r1.status_code == 200, f'search failed: {r1.text}'; assert r2.status_code == 200, f'permissions failed: {r2.text}'; print('BOTH ENDPOINTS HTTP 200 OK')"
   ```

2. **Execute Full Test Suite**:
   ```powershell
   python -m unittest tests.e2e.test_tier1_features
   python tests/e2e/runner.py --milestone M5
   python tests/e2e/runner.py
   ```

3. **Verify Zero UI Drift**:
   ```powershell
   git status --porcelain src/
   ```
