# Milestone M5 Iteration 2 Investigation Report: Gateway Endpoints Fix

**Agent**: `explorer_m5_iter2_1`  
**Role**: Teamwork Explorer (investigation, synthesis)  
**Milestone**: M5 Iteration 2 (Unified REST Gateway Fixes)  
**Working Directory**: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m5_iter2_1\`  
**Target Code**:
- `backend/main.py` (lines 427–432, 485–497)
- `backend/memory/hybrid_rag.py` (lines 332–345)
- `backend/core/tool_dispatcher.py` (lines 85–97)

---

## 1. Observation

### 1.1 Direct Defect Reproduction

Running the challenger test suite `tests.test_challenger_m5_gateway_ws` reproduced the two HTTP 500 endpoint crashes verbatim:

- **Command**:
  ```powershell
  python -m unittest tests.test_challenger_m5_gateway_ws
  ```
- **Result Summary**: `FAILED (failures=2, tests=19)`
- **Verbatim Error 1 (`/search`)**:
  ```
  FAIL: test_06_search_endpoint (tests.test_challenger_m5_gateway_ws.TestGatewayRestEndpoints.test_06_search_endpoint)
  Verify GET /search?q=test interacts with HybridMemory without error.
  ----------------------------------------------------------------------
  Traceback (most recent call last):
    File "E:\Projects\J.A.R.V.I.S Electron App\tests\test_challenger_m5_gateway_ws.py", line 134, in test_06_search_endpoint
      self.assertEqual(
  AssertionError: 500 != 200 : GET /search failed with status 500: {"status":"error","message":"HybridMemory.search() got an unexpected keyword argument 'limit'","code":"INTERNAL_GATEWAY_ERROR"}
  ```

- **Verbatim Error 2 (`/v1/permissions`)**:
  ```
  FAIL: test_11_permissions_endpoints (tests.test_challenger_m5_gateway_ws.TestGatewayRestEndpoints.test_11_permissions_endpoints)
  Verify GET /v1/permissions, POST grant, POST revoke.
  ----------------------------------------------------------------------
  Traceback (most recent call last):
    File "E:\Projects\J.A.R.V.I.S Electron App\tests\test_challenger_m5_gateway_ws.py", line 206, in test_11_permissions_endpoints
      self.assertEqual(
  AssertionError: 500 != 200 : GET /v1/permissions failed with status 500: {"status":"error","message":"'name'","code":"INTERNAL_GATEWAY_ERROR"}
  ```

- **Direct Probe Execution**:
  ```powershell
  python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app, raise_server_exceptions=False); print('/search:', c.get('/search?q=test').status_code, c.get('/search?q=test').json()); print('/v1/permissions:', c.get('/v1/permissions').status_code, c.get('/v1/permissions').json())"
  ```
  **Output**:
  ```
  /search: 500 {'status': 'error', 'message': "HybridMemory.search() got an unexpected keyword argument 'limit'", 'code': 'INTERNAL_GATEWAY_ERROR'}
  /v1/permissions: 500 {'status': 'error', 'message': "'name'", 'code': 'INTERNAL_GATEWAY_ERROR'}
  ```

---

### 1.2 Inspection of Source Code

#### Bug 1: `/search` Argument Mismatch
- **File**: `backend/main.py`, lines 427–432:
  ```python
  427: @app.get("/search")
  428: async def search(q: str = Query("")) -> Dict[str, Any]:
  429:     fts_results = state_db.search_fts(q, limit=20)
  430:     hybrid_results = hybrid_memory.search(q, limit=10)
  431:     return {"query": q, "results": fts_results, "hybrid_hits": hybrid_results}
  ```
- **Definition in `backend/memory/hybrid_rag.py`**, lines 332–337:
  ```python
  332:     def search(
  333:         self,
  334:         query: str,
  335:         top_k: int = 5,
  336:         min_score: float = 0.0,
  337:     ) -> List[SearchResult]:
  ```
- **Direct Cause**: `hybrid_memory.search` specifies `top_k: int = 5` and does not define a `limit` parameter. Passing `limit=10` causes Python to raise `TypeError: HybridMemory.search() got an unexpected keyword argument 'limit'`, which the gateway exception handler intercepts and converts into HTTP 500 (`INTERNAL_GATEWAY_ERROR`).

#### Bug 2: `/v1/permissions` Unhandled KeyError
- **File**: `backend/main.py`, lines 485–497:
  ```python
  485: @app.get("/v1/permissions")
  486: async def get_permissions() -> Dict[str, Any]:
  487:     tools = tool_dispatcher.get_tool_definitions()
  488:     perms = {
  489:         t["name"]: {
  490:             "scope": "*",
  491:             "granted": True,
  492:             "risk_level": t.get("risk_level", "LOW"),
  493:         }
  494:         for t in tools
  495:     }
  496:     return {"permissions": perms}
  ```
- **Definition in `backend/core/tool_dispatcher.py`**, lines 85–97:
  ```python
  85:     def get_tool_definitions(self) -> List[Dict[str, Any]]:
  86:         """Returns schemas formatted for LLM tool selection."""
  87:         defs = []
  88:         for name, desc in self._tool_descriptions.items():
  89:             defs.append({
  90:                 "type": "function",
  91:                 "function": {
  92:                     "name": name,
  93:                     "description": desc,
  94:                     "parameters": {"type": "object", "properties": {}},
  95:                 },
  96:             })
  97:         return defs
  ```
- **Direct Cause**: Tool definitions conform to the standard OpenAI / OpenAPI function schema:
  `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`.
  There is no `"name"` key at the top level `t["name"]`. Accessing `t["name"]` throws `KeyError: 'name'`, triggering HTTP 500.

---

## 2. Logic Chain

1. **Step 1 (Root Cause for `/search`)**:
   - `backend/main.py:430` calls `hybrid_memory.search(q, limit=10)`.
   - `HybridMemory.search()` in `backend/memory/hybrid_rag.py:332` only accepts `query`, `top_k`, and `min_score`.
   - Passing `limit=10` triggers a `TypeError`.
   - Modifying `backend/main.py:430` to `hybrid_memory.search(q, top_k=10)` satisfies `HybridMemory.search`'s exact signature.
   - Additionally, adding `limit: Optional[int] = None` as an alias in `HybridMemory.search` guards against any caller interchangeably using `limit` or `top_k`, enhancing defensive robustness.

2. **Step 2 (Root Cause for `/v1/permissions`)**:
   - `backend/main.py:488–495` iterates over `tools = tool_dispatcher.get_tool_definitions()`.
   - Each element `t` produced by `ToolDispatcher` has structure `{"type": "function", "function": {"name": ..., ...}}`.
   - Because `t` lacks a top-level key `"name"`, `t["name"]` raises `KeyError: 'name'`.
   - Safe extraction requires querying both `t.get("name")` and `t.get("function", {}).get("name")`, with fallback to `str(t)` if neither is present.
   - Similarly, `risk_level` must safely inspect `t.get("risk_level")` or `t.get("function", {}).get("risk_level")`, defaulting to `"LOW"`.
   - Executing this logic in Python successfully resolves all 18 tool permissions without errors.

---

## 3. Caveats

1. **Read-Only Explorer Boundary**:
   - As an explorer agent, no modifications were directly applied to `backend/main.py` or `backend/memory/hybrid_rag.py`. Concrete, copy-pasteable patches are provided for the implementation worker.
2. **Simulation / Fallback Context**:
   - The test environment runs without dedicated GPU/hardware sensors; `CameraHub`, `DeepFaceSentry`, and `ModelRouter` correctly use their mock/simulated fallbacks.
3. **OpenAI Schema Uniformity**:
   - All standard tools in `ToolDispatcher` adhere to `{"type": "function", "function": {...}}`. The proposed permissions parsing logic is dual-compatible: it handles nested OpenAPI formats, flat schemas (`{"name": ...}`), and arbitrary dictionaries.

---

## 4. Conclusion & Concrete Blueprint

Both bugs can be remediated with precision in `backend/main.py` (and optionally hardened in `backend/memory/hybrid_rag.py`).

### 4.1 Fix 1: `backend/main.py` Line 430 (`/search`)

#### Before (lines 427–432):
```python
@app.get("/search")
async def search(q: str = Query("")) -> Dict[str, Any]:
    fts_results = state_db.search_fts(q, limit=20)
    hybrid_results = hybrid_memory.search(q, limit=10)
    return {"query": q, "results": fts_results, "hybrid_hits": hybrid_results}
```

#### After (lines 427–432):
```python
@app.get("/search")
async def search(q: str = Query("")) -> Dict[str, Any]:
    fts_results = state_db.search_fts(q, limit=20)
    hybrid_results = hybrid_memory.search(q, top_k=10)
    return {"query": q, "results": fts_results, "hybrid_hits": hybrid_results}
```

---

### 4.2 Fix 2: `backend/main.py` Lines 485–497 (`/v1/permissions`)

#### Before (lines 485–497):
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

#### After (lines 485–497):
```python
@app.get("/v1/permissions")
async def get_permissions() -> Dict[str, Any]:
    tools = tool_dispatcher.get_tool_definitions()
    perms: Dict[str, Any] = {}
    for t in tools:
        if not isinstance(t, dict):
            continue
        func_dict = t.get("function") if isinstance(t.get("function"), dict) else {}
        name = t.get("name") or func_dict.get("name") or str(t)
        risk_level = t.get("risk_level") or func_dict.get("risk_level", "LOW")
        perms[name] = {
            "scope": "*",
            "granted": True,
            "risk_level": risk_level,
        }
    return {"permissions": perms}
```

---

### 4.3 Recommended Hardening: `backend/memory/hybrid_rag.py` Lines 332–342 (`search()` alias)

To make `HybridMemory.search` robust against both parameter naming styles:

#### Before (lines 332–341):
```python
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Performs hybrid lexical and vector search with RRF k=60 fusion."""
        if not query or not query.strip():
            return []
```

#### After (lines 332–344):
```python
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        limit: Optional[int] = None,
    ) -> List[SearchResult]:
        """Performs hybrid lexical and vector search with RRF k=60 fusion."""
        if limit is not None:
            top_k = limit

        if not query or not query.strip():
            return []
```

---

## 5. Verification Method

Once Worker M5 applies these patches:

1. **Verify Probes Return HTTP 200**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from backend.main import app; c = TestClient(app, raise_server_exceptions=False); r_search = c.get('/search?q=test'); r_perms = c.get('/v1/permissions'); print('/search status:', r_search.status_code); print('/v1/permissions status:', r_perms.status_code); assert r_search.status_code == 200, r_search.text; assert r_perms.status_code == 200, r_perms.text; print('PROBE VERIFICATION PASSED: BOTH HTTP 200 OK')"
   ```
   - **Expected Output**:
     ```
     /search status: 200
     /v1/permissions status: 200
     PROBE VERIFICATION PASSED: BOTH HTTP 200 OK
     ```

2. **Run Challenger Stress Test Suite**:
   ```powershell
   python -m unittest tests.test_challenger_m5_gateway_ws
   ```
   - **Expected Output**: `Ran 19 tests in ~0.4s ... OK` (0 failures, 0 errors).

3. **Run Milestone M5 Unified Test Runner**:
   ```powershell
   python tests/e2e/runner.py --milestone M5
   ```
   - **Expected Output**: `Passed: 50, Skipped: 0, Failed: 0, RESULT: SUCCESS`.

4. **Verify Full E2E Test Suite**:
   ```powershell
   python tests/e2e/runner.py
   ```
   - **Expected Output**: `Passed: 250, Skipped: 0, Failed: 0, RESULT: SUCCESS`.

5. **UI Immutability Audit**:
   ```powershell
   git status --porcelain src/
   ```
   - **Expected Output**: No modifications outside approved Milestone M1 files.

### Invalidation Conditions
- Any occurrence of HTTP 500 when accessing `GET /search?q=...` or `GET /v1/permissions`.
- Any regression in WebSocket connection handling or message routing.
