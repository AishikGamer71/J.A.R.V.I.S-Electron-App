# Repository Restructure Plan: J.A.R.V.I.S. Desktop Assistant

**Status:** Awaiting User Approval ("GO")  
**Branch:** `chore/restructure`  
**Baseline Tag:** `pre-restructure`  

---

## 1. Objectives & Principles

1. **Structure Only:** Zero logic refactoring, zero behavioral modifications, zero dependency upgrades.
2. **History Preservation:** Every tracked file will be moved using `git mv`.
3. **Canonical Boundaries:**
   - `apps/desktop/`: Unified Electron + React 19 frontend shell.
   - `services/backend/`: Python 3.11 FastAPI sidecar backend and pytest suite.
   - `config/persona/`: Runtime product files (agent personas, capability specs, prompt templates).
   - `.agents/`: Development-time agent guidelines, rules, and curated ECC skills.
   - `%APPDATA%\JARVIS\`: All runtime data (fallback `.data/`, gitignored).
4. **Clean Single Source of Truth:** Elimination of 45 redundant root-level agent directories containing duplicate skill files and broken symlinks.

---

## 2. Target Layout Overview

```
J.A.R.V.I.S Electron App/
├── .agents/
│   ├── rules/
│   │   ├── jarvis-project.md
│   │   └── karpathy-guidelines.md
│   ├── skills/
│   │   ├── README.md
│   │   └── ecc-*/SKILL.md (curated ECC skills, max 12)
│   ├── workflows/
│   │   └── .gitkeep
│   └── mcp_config.json
├── apps/
│   └── desktop/
│       ├── electron/           # Main process, preload, IPC handlers
│       ├── src/                # React 19 renderer HUD, holographic core, tabs
│       ├── public/             # Static public web assets
│       ├── assets/             # Icons, app branding
│       ├── index.html          # HTML entry point
│       ├── vite.config.ts      # Vite bundler configuration
│       ├── tsconfig.json       # Renderer TypeScript config
│       ├── tsconfig.electron.json # Main process TypeScript config
│       ├── tsconfig.e2e.json   # E2E TypeScript config
│       ├── vitest.config.ts    # Vitest configuration
│       └── vitest.setup.ts     # Vitest DOM/environment setup
├── services/
│   └── backend/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py         # FastAPI application entry point
│       │   ├── api/            # REST and WebSocket endpoints
│       │   ├── core/           # Prompt builder, compressor, scheduler
│       │   ├── brain/          # HermesBrain conversation loop & orchestrator
│       │   ├── voice/          # STT, TTS, wakeword engine, audio pipeline
│       │   ├── os_control/     # Windows MCP automation, browser-use, Agent-S3
│       │   ├── memory/         # SQLite WAL state DB, hybrid RAG memory
│       │   ├── security/       # AgentShield, ECC security hooks
│       │   ├── senses/         # Camera hub, biometrics, gestures, web crawling
│       │   ├── hardware/       # Hardware profiler, power telemetry
│       │   ├── engine/         # Model router, token streaming
│       │   └── schemas/        # Pydantic data schemas
│       ├── tests/              # Backend pytest suite & adversarial checks
│       ├── .venv/              # Dedicated Python 3.11 virtual environment
│       └── pyproject.toml      # Python dependencies & pytest configuration
├── config/
│   └── persona/
│       ├── agents/             # architect.md, planner.md, security_auditor.md
│       └── skills/             # Runtime capabilities (browser, deep_research, desktop_control, etc.)
├── scripts/                    # Build, bundle, verify, and packaging scripts
├── docs/                       # baseline.md, restructure-plan.md, plugins.md, etc.
├── .gitignore
├── .env.example
├── AGENTS.md                   # Lean project map (<4,000 chars)
├── LICENSE
├── package.json                # Root orchestration scripts
└── README.md
```

---

## 3. Path Migration Mapping (Old → New)

### Area A: Desktop Frontend (`apps/desktop/`)
| Source Path (Old) | Target Path (New) | Move Method |
|---|---|---|
| `electron/` | `apps/desktop/electron/` | `git mv electron apps/desktop/electron` |
| `src/` | `apps/desktop/src/` | `git mv src apps/desktop/src` |
| `public/` | `apps/desktop/public/` | `git mv public apps/desktop/public` |
| `assets/` | `apps/desktop/assets/` | `git mv assets apps/desktop/assets` |
| `index.html` | `apps/desktop/index.html` | `git mv index.html apps/desktop/index.html` |
| `vite.config.ts` | `apps/desktop/vite.config.ts` | `git mv vite.config.ts apps/desktop/vite.config.ts` |
| `tsconfig.json` | `apps/desktop/tsconfig.json` | `git mv tsconfig.json apps/desktop/tsconfig.json` |
| `tsconfig.electron.json` | `apps/desktop/tsconfig.electron.json` | `git mv tsconfig.electron.json apps/desktop/tsconfig.electron.json` |
| `tsconfig.e2e.json` | `apps/desktop/tsconfig.e2e.json` | `git mv tsconfig.e2e.json apps/desktop/tsconfig.e2e.json` |
| `vitest.config.ts` | `apps/desktop/vitest.config.ts` | `git mv vitest.config.ts apps/desktop/vitest.config.ts` |
| `vitest.setup.ts` | `apps/desktop/vitest.setup.ts` | `git mv vitest.setup.ts apps/desktop/vitest.setup.ts` |
| `components.json` | `apps/desktop/components.json` | `git mv components.json apps/desktop/components.json` |
| `eslint.config.mjs` | `apps/desktop/eslint.config.mjs` | `git mv eslint.config.mjs apps/desktop/eslint.config.mjs` |
| `e2e/` | `apps/desktop/e2e/` | `git mv e2e apps/desktop/e2e` |
| `playwright.config.ts` | `apps/desktop/playwright.config.ts` | `git mv playwright.config.ts apps/desktop/playwright.config.ts` |

### Area B: Backend Sidecar (`services/backend/`)
| Source Path (Old) | Target Path (New) | Move Method |
|---|---|---|
| `backend/main.py` | `services/backend/app/main.py` | `git mv` |
| `backend/__init__.py` | `services/backend/app/__init__.py` | `git mv` |
| `backend/api/` | `services/backend/app/api/` | `git mv` |
| `backend/core/hermes_brain.py` | `services/backend/app/brain/hermes_brain.py` | `git mv` |
| `backend/core/` (remainder) | `services/backend/app/core/` | `git mv` |
| `backend/voice/` | `services/backend/app/voice/` | `git mv` |
| `backend/automation/` | `services/backend/app/os_control/` | `git mv` |
| `backend/memory/` | `services/backend/app/memory/` | `git mv` |
| `backend/security/` | `services/backend/app/security/` | `git mv` |
| `backend/senses/` | `services/backend/app/senses/` | `git mv` |
| `backend/hardware/` | `services/backend/app/hardware/` | `git mv` |
| `backend/engine/` | `services/backend/app/engine/` | `git mv` |
| `backend/schemas/` | `services/backend/app/schemas/` | `git mv` |
| `tests/` (Python tests) | `services/backend/tests/` | `git mv` |
| `native_core/` | `services/backend/native_core/` | `git mv` |

### Area C: Runtime Persona & Capabilities (`config/persona/`)
| Source Path (Old) | Target Path (New) | Move Method |
|---|---|---|
| `backend/agents/*.md` | `config/persona/agents/*.md` | `git mv` |
| `backend/skills/*.md` | `config/persona/skills/*.md` | `git mv` |

### Area D: Agent Skills & Guidelines Consolidation (`.agents/`)
| Source Path (Old) | Target Path (New) | Move Method |
|---|---|---|
| `.agents/rules/jarvis-project.md` | `.agents/rules/jarvis-project.md` | Keep & update path rules |
| `CLAUDE.md` (from `andrej-karpathy-skills`) | `.agents/rules/karpathy-guidelines.md` | Import |
| Curated ECC skills (≤12) from `affaan-m/ECC` | `.agents/skills/ecc-*/SKILL.md` | Clone & import |
| `.agents/skills/README.md` | `.agents/skills/README.md` | Document source commit SHA |

---

## 4. Proposed Removals & Justifications

| Path | Reason for Removal |
|---|---|
| 45 dot-directories at root: `.adal`, `.aider-desk`, `.augment`, `.autohand`, `.bob`, `.claude`, `.codeartsdoer`, `.codebuddy`, `.codemaker`, `.codestudio`, `.commandcode`, `.continue`, `.cortex`, `.crush`, `.devin`, `.forge`, `.goose`, `.grok`, `.hermes`, `.iflow`, `.inferencesh`, `.jazz`, `.junie`, `.kimchi`, `.kiro`, `.kode`, `.lingma`, `.mcpjam`, `.minimax`, `.moxby`, `.mux`, `.neovate`, `.ona`, `.openhands`, `.pochi`, `.posit`, `.qoder`, `.qwen`, `.reasonix`, `.roo`, `.rovodev`, `.tabnine`, `.terramind`, `.tinycloud`, `.trae`, `.vibe`, `.windsurf`, `.zcode`, `.zencoder` | **Redundant Clones & Dead Symlinks:** Dumped in commit 68cd46a, these 45 folders contain identical copies of 13 skill files and hundreds of broken filesystem symlinks. Consolidating into the single canonical `.agents/` directory satisfies Step 3 and removes 585 redundant tracked files. |
| `showcase_screenshots/` | Historical static screenshots (not required for runtime/build). |
| `test-results/`, `playwright-report/` | Stale build artifacts accidentally tracked in git. |
| `test-run.log`, `electron-debug.log`, `repo_inventory.txt` | Temporary diagnostic log files (gitignored). |

---

## 5. Configuration Files Referencing Paths & Required Updates

1. **Root `package.json`:**
   - Update scripts to point to `apps/desktop/` and `services/backend/`:
     - `dev:renderer`: `"vite --config apps/desktop/vite.config.ts"`
     - `typecheck`: `"tsc -p apps/desktop --noEmit && tsc -p apps/desktop/tsconfig.electron.json --noEmit"`
     - `build:python`: `"python -m compileall services/backend/app"`
     - `test:backend`: `"pytest services/backend/tests"`
     - Update `main` entry point and build configurations.
2. **`apps/desktop/vite.config.ts`:**
   - Update root and aliases (`@` and `@renderer` resolving to `apps/desktop/src`).
   - Update `fs.allow` whitelist for assets and root dependencies.
3. **`apps/desktop/tsconfig*.json`:**
   - Update relative path references (`../../` as needed).
4. **`electron/jarvis-service-runtime.ts` (now in `apps/desktop/electron/`):**
   - Update path resolution for sidecar: `services/backend/app/main.py`.
   - Update `PYTHONPATH` assembly to include `services/backend`.
   - Update packaged binary lookup: `process.resourcesPath/backend/jarvis-sidecar.exe`.
5. **`scripts/run-jarvis-service.mjs`:**
   - Update Python module name to `app.main:app` and cwd to `services/backend`.
6. **`scripts/bundle-electron-main.mjs`:**
   - Update entry points to `apps/desktop/electron/main.ts` and `apps/desktop/electron/preload.ts`.
7. **Python Modules in `services/backend/app/`:**
   - Update internal package imports from `from backend.x import y` to `from app.x import y`.
8. **Python Tests in `services/backend/tests/`:**
   - Configure `PYTHONPATH` so imports `from app.main import app` resolve reliably.

---

## 6. Verification Gate Alignment

Once approved ("GO"), the restructuring will execute in four atomic commits:
1. `chore(desktop): move electron and renderer into apps/desktop`
2. `chore(backend): move python services into services/backend`
3. `chore(persona): move persona and capability specs into config/persona`
4. `chore(agents): consolidate .agents with curated ECC skills and Karpathy guidelines`

Then path fixes will be applied and verified against `scripts/verify.ps1`.
