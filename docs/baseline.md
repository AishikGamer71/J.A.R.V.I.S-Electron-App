# Baseline Report: J.A.R.V.I.S. Desktop Assistant

**Date:** 2026-11-15  
**Platform:** Windows 11 (PowerShell)  
**Branch:** `chore/restructure`  
**Baseline Tag:** `pre-restructure`  
**Git Commit SHA:** `10261d82e80f`

---

## 1. Executive Summary & Repository Status

A full read-only baseline audit of the repository was conducted before any structural moves or refactoring. The repository contains an Electron/React HUD frontend and a Python 3.11 FastAPI sidecar backend.

### Git Status
- Working tree clean on branch `chore/restructure` (branched from `main` at `10261d8`).
- Tag `pre-restructure` successfully created at `10261d8`.
- Total tracked files in git: **1,172**.
- **Important Finding:** There are 45 duplicate agent directories at the repository root (`.adal`, `.aider-desk`, `.augment`, `.autohand`, `.bob`, `.claude`, `.devin`, `.hermes`, etc.) each containing 13 tracked files that are identical copies of skills plus numerous broken symlinks pointing outside the repository. Commit `10261d8` migrated `.agents/` with 16 curated files.

---

## 2. Entry Points

| Layer | Entry Point File | Build/Runtime Mechanism |
|---|---|---|
| **Frontend Renderer** | `src/main.tsx` (`index.html`) | React 19, Vite 8, Tailwind CSS, `@` alias pointing to `src/` |
| **Electron Main Process** | `electron/main.ts` | Bundled via esbuild (`scripts/bundle-electron-main.mjs`) to `dist/electron-main.mjs` |
| **Electron Preload** | `electron/preload.ts` | Bundled via esbuild to `dist/electron-preload.js` |
| **Backend Sidecar** | `backend/main.py` | FastAPI application (`app = FastAPI(...)`), uvicorn module `backend.main:app` |
| **Standalone Runner** | `scripts/run-jarvis-service.mjs` | Node.js script spawning Python uvicorn on port 8765 |

---

## 3. Build & Health Status TODAY

### A. TypeScript Typechecking (`npm run typecheck`)
- **Command:** `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`)
- **Status:** **PASS** (Exit Code: 0)
- **Evidence:** Clean exit across all 3 tsconfigs (root/renderer, electron, e2e).

### B. Frontend Production Build (`npm run build`)
- **Command:** `npm run build` (`vite build && node scripts/bundle-electron-main.mjs && node scripts/stage-native-deps.mjs`)
- **Status:** **PASS** (Exit Code: 0)
- **Evidence:**
  - `dist/index.html` (1.28 kB)
  - `dist/assets/index-*.css` (149.82 kB)
  - `dist/assets/index-*.js` (3,365.29 kB)
  - `dist/electron-main.mjs` (2.7 MB)
  - `dist/electron-preload.js` (20.3 kB)
  - `node-pty` native dependencies staged to `dist/node_modules/node-pty`
  - `scripts/assert-dist-built.mjs` verified output existence.

### C. Vitest Unit & Integration Suite (`npm test`)
- **Command:** `npm test` (`vitest run`)
- **Status:** **PRE-EXISTING FAILURES** (68 passed, 1 skipped, 2 failed out of 71 files; 794 passed, 2 skipped, 3 failed out of 799 tests)
- **Pre-existing Failures:**
  1. `electron/git-worktree-ops.test.ts > listBranches: a branch claimed by a worktree is flagged checked out`: Timeout after 5000ms on Windows Git subprocess.
  2. `electron/jarvis-service-runtime.test.ts > J.A.R.V.I.S local service runtime > prefers the project virtual environment over a system Python`: Expected `C:\work\jarvis-core\.venv\Scripts\python.exe`, received `python.exe`.
  3. `electron/jarvis-service-runtime.test.ts > J.A.R.V.I.S local service runtime > isolates J.A.R.V.I.S data while preserving an existing PYTHONPATH`: Expected `\app-data\core\jarvis.db`, received `<workspace>\storage\jarvis_memory.db`.

### D. Python Backend Boot & Health (`GET /health`)
- **Command:** `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8769`
- **Status:** **PASS** (Exit Code: 0)
- **Evidence:** Server launched in 2.76s; `GET http://127.0.0.1:8769/health` returned HTTP 200 with JSON payload:
  ```json
  {
    "status": "healthy",
    "service": "jarvis-core-service",
    "version": "2.0.0",
    "model_status": "ready",
    "engine": "local_heuristic",
    "voice": "active",
    "vision": "ready",
    "mobile": "ready",
    "uptime_seconds": 2.76,
    "subsystems": {
      "brain": "online",
      "shield": "active",
      "state_db": "wal_ready",
      "telemetry": "sampling",
      "power": { "power_state": "ac_desktop", "conservation_tier": 0 }
    }
  }
  ```

### E. Pytest Suite (`python -m pytest tests`)
- **Command:** `.\.venv\Scripts\python.exe -m pytest tests`
- **Status:** **PRE-EXISTING FAILURES** (615 passed, 23 failed out of 638 items)
- **Pre-existing Failures Breakdown:**
  1. *Rule File Drift Tests (5 failures)*: `test_tier1_features.py::TestTier1Milestone1Features::test_f04_01` through `f04_05` check for deprecated `.antigravity/rules.md` and `.agent/rules/rules.md` (which were consolidated to `.agents/rules/`).
  2. *Governance Parity Tests (3 failures)*: `test_challenger_empirical_m1.py::test_c07`, `test_m1_adversarial.py::test_governance_rules_clauses_presence`, and `test_governance_rules_exact_character_parity` similarly assert exact character hashes of deleted `.antigravity/rules.md`.
  3. *Playwright Python Tests (10 failures)*: `test_challenger_m4_iter2_1.py` tests fail due to missing Chromium/Playwright browser binaries in the Windows Python virtualenv.
  4. *Subsystem Unit & Latency Checks (5 failures)*:
     - `test_adversarial_m4.py::test_browser_use_url_security_filtering`
     - `test_adversarial_m6_automation_senses.py::test_03_table_conversion`
     - `test_challenger_empirical_m1.py::test_c03_tools_endpoints`
     - `test_challenger_empirical_m1.py::test_c05_websocket_protocol_full_matrix`
     - `test_m2_adversarial_deep.py::test_mid_stream_interrupt_latency_sub_32ms` (exceeded 32ms deadline on Windows).

### F. Package.json Backend Test Script (`npm run test:backend`)
- **Command:** `npm run test:backend`
- **Status:** **PRE-EXISTING FAILURE**
- **Evidence:** `package.json` references `backend/test_backend.py`, which does not exist on disk.

---

## 4. How Electron Locates and Launches the Backend

The lifecycle is managed by `electron/jarvis-service-runtime.ts` and `scripts/run-jarvis-service.mjs`:

1. **Python Interpreter Resolution:**
   - Checks `process.env.JARVIS_PYTHON`.
   - In packaged production mode (`app.isPackaged`), checks `process.resourcesPath/backend/jarvis-sidecar.exe`.
   - In development mode, checks `<workspaceRoot>/.venv/Scripts/python.exe`.
   - Fallback: System `python.exe` (Windows) or `python3` (POSIX).

2. **Module & Arguments:**
   - Checks if `backend/main.py` exists; sets module to `backend.main:app` (otherwise `backend.server:app`).
   - Spawns: `[python, '-u', '-m', 'uvicorn', appModule, '--host', '127.0.0.1', '--port', '8765']`.

3. **Environment & Data Isolation:**
   - `DATA_DIR`: Set to `%APPDATA%\JARVIS\core` (via `appDataDir`).
   - `DATABASE_PATH`: Set to `<workspaceRoot>\storage\jarvis_memory.db`.
   - `PYTHONPATH`: Prepends workspace root and service root.
   - `VIRTUAL_ENV`: Points to `<workspaceRoot>\.venv`.

4. **Health Probe & Teardown:**
   - Polls `GET http://127.0.0.1:8765/health` every 500ms for up to 30s.
   - Requires response `body.status === 'healthy'` before reporting sidecar online.
   - On exit or failure, uses process-tree kill (`taskkill /F /T /PID <pid>`) via `backend-child.ts` to ensure zero orphaned `python.exe` processes.

---

## 5. Actual Backend Routes Called by Renderer & Main

Verification was performed by auditing calls in `src/` and `electron/` against `backend/main.py`:

| Consumer File | Route / Endpoint | Protocol / Method | Handler in `backend/main.py` | Status |
|---|---|---|---|---|
| `src/lib/gateway-client.ts` | `/ws/jarvis` | WebSocket | `@app.websocket("/ws/jarvis")` | Active & Wired |
| `src/services/jarvis-voice-ai.ts` | `/ws/jarvis` | WebSocket | `@app.websocket("/ws/jarvis")` | Active & Wired |
| `src/services/jarvisBridge.ts` | `/ws` | WebSocket | `@app.websocket("/ws")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/health` | HTTP GET | `@app.get("/health")` | Active & Wired |
| `electron/jarvis-handlers.ts` | `/health` | HTTP GET | `@app.get("/health")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/chat/completions` | HTTP POST | `@app.post("/v1/chat/completions")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/sessions` | HTTP GET / POST | `@app.get("/sessions")`, `@app.post("/sessions")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/sessions/{id}/messages`| HTTP GET | `@app.get("/sessions/{session_id}/messages")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/sessions/{id}` | HTTP DELETE | `@app.delete("/sessions/{session_id}")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/search?q={query}` | HTTP GET | `@app.get("/search")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/tools` | HTTP GET | `@app.get("/v1/tools")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/tools/invoke` | HTTP POST | `@app.post("/v1/tools/invoke")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/core-memory` | HTTP GET / POST | `@app.get("/v1/core-memory")`, `@app.post("/v1/core-memory")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/permissions` | HTTP GET | `@app.get("/v1/permissions")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/permissions/grant` | HTTP POST | `@app.post("/v1/permissions/grant")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/permissions/revoke`| HTTP POST | `@app.post("/v1/permissions/revoke")`| Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/agents` | HTTP GET | `@app.get("/v1/agents")` | Active & Wired |
| `src/lib/gateway-client.ts` | `/v1/agents/execute` | HTTP POST | `@app.post("/v1/agents/execute")` | Active & Wired |
| `src/pages/dashboard.tsx` | `/api/env` | HTTP GET | `@app.get("/api/env")` | Active & Wired |
| `src/pages/settings.tsx` | `/api/env` | HTTP POST | `@app.post("/api/env")` | Active & Wired |
| `electron/jarvis-handlers.ts` | `/api/env` | HTTP GET / POST | `@app.get("/api/env")`, `@app.post("/api/env")` | Active & Wired |

**Findings on Wiring:**
- The Python FastAPI backend is **NOT orphaned**; both the Electron main process and the React renderer actively consume REST routes and dual WebSocket streams (`/ws` and `/ws/jarvis`).
- Voice streaming is wired via WebSocket at `/ws/jarvis` and managed by `jarvis-voice-ai.ts` and `audio_pipeline.py`.

---

## 6. Vendored & Upstream-Derived Directories

- **Nous Research Hermes Agent Shell:**
  - The desktop shell (`electron/`, `src/`, `scripts/`, `assets/`, `public/`) is derived from Nous Research's Hermes Agent desktop app (`apps/desktop` in upstream hermes-agent), as stated in `LICENSE`: `Copyright (c) 2024-2026 Nous Research Inc. (Hermes Agent desktop shell and core components)`.
  - It contains upstream desktop infrastructure (SSH connection management, update relaunchers, window state persistence) integrated with the J.A.R.V.I.S HUD components.
  - Per the target architecture, this shell moves cleanly into `apps/desktop/` with internals intact.
