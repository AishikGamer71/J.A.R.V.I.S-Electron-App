# AGENTS.md — J.A.R.V.I.S. Desktop System

> Project instructions for every agent session. The source rules are in `.agents/rules/`.

## Identity

J.A.R.V.I.S. — Windows desktop AI assistant. Electron + React 19 HUD frontend, Python 3.11 FastAPI sidecar backend.

## Project Map

| Subsystem | Location | Entry Point / Tech |
|---|---|---|
| **Frontend HUD** | `apps/desktop/` | `apps/desktop/src/main.tsx` (React 19, Tailwind) |
| **Electron Shell**| `apps/desktop/` | `apps/desktop/electron/main.ts` (esbuild, IPC) |
| **Backend Sidecar** | `services/backend/` | `services/backend/app/main.py` (FastAPI, SQLite WAL) |
| **Backend Tests** | `services/backend/tests/` | pytest suite & adversarial benchmarks |
| **Runtime Personas** | `config/persona/` | Product markdown files (`agents/`, `skills/`) |
| **Scripts** | `scripts/` | `scripts/verify.ps1`, `run-jarvis-service.mjs` |
| **Agent Config** | `.agents/` | Rules (`.agents/rules/`), curated skills (`.agents/skills/`) |
| **Runtime Data** | `%APPDATA%\JARVIS\` | Outside repo (dev fallback `.data/`, gitignored) |

## Dev / Build / Verify Commands

- **Verify All Gates**: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
- **Verify Full E2E (Phase 2C)**: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Full`
- **Frontend Typecheck**: `npm run typecheck`
- **Frontend Build**: `npm run build`
- **Unit & Desktop Tests**: `npm test`
- **Backend Tests**: `npm run test:backend` (or `pytest services/backend/tests`)
- **Backend Standalone**: `npm run sidecar` (`node scripts/run-jarvis-service.mjs`)
- **Full Dev Mode**: `npm run dev` (spawns renderer on :5174 and Electron)
- **Production Package**: `npm run pack` (`electron-builder --dir`)

## Conventions & Non-Negotiables

1. **Desktop Only:** Windows 11 target. No web or mobile ports.
2. **Locked Visuals:** Do not modify UI layout/visuals in `apps/desktop/src/components/common/**`, `dashboard/**`, or navigation tabs without explicit instructions.
3. **Surgical Changes:** Minimum code that solves the issue. Match surrounding style.
4. **No Dead Code:** Delete unused code immediately; do not comment it out.
5. **Failures & Secrets:** Never hide failures (label PRE-EXISTING). Never print or commit secrets (`.env` untracked, maintain `.env.example`).
6. **Hardware Safety:** Exclusively `camera_hub.py` owns camera handles; exclusively `realtime_stt.py` owns mic handles.

## Agent Skills & Guidelines

- **Rules (`.agents/rules/`)**:
  - `karpathy-guidelines.md`: Always-on core principles (simplicity, surgical changes, goal-driven execution).
  - `jarvis-project.md`: Project constraints, hardware rules, security, and allowed edit paths.
- **Skills (`.agents/skills/`)**:
  - Curated ECC skills prefixed with `ecc-` (max 12, documented in `.agents/skills/README.md`).
  - Covers TypeScript/React/Electron, Python/FastAPI, TDD/verification, security, and search-first.

## Working rules

- Think first. Trace the request through its callers, fixtures, config and tests. State material assumptions and ask about decisions that change behavior.
- Start simple. Reuse project code, then platform or standard-library features, then installed dependencies. Add only what the task needs.
- Work surgically. Match the surrounding code. Preserve contracts, input validation, accessibility, hardware calibration, permission gates and error handling.
- Verify the goal. Reproduce a failure first, run the smallest meaningful check, then run the project gates. Report failures and verification limits.
- Follow the current task's approval points. Check static references, dynamic dispatch, packaging and documented capabilities before proposing removal.
- Keep the HUD shell, widgets, public assets and build configuration within the edit boundaries in `.agents/rules/jarvis-project.md`. Preserve the existing navigation tabs.
- Route browsing through background CDP, document reading through MarkItDown, and Windows automation through its UI Automation bridge. Exclude the Electron HWND.
- Preserve ECC pre/post hooks, AgentShield checks and the Ctrl+Alt+Backspace emergency abort.
- For a simplification audit use `$ponytail-audit`, review diffs with `$ponytail-review`, and collect explicit shortcut markers with `$ponytail-debt`. The four upstream Markdown skills share the license at `.agents/skills/ponytail/LICENSE`.
