# DISPATCH: worker_m1 (Milestone M1 Implementation)

## Identity & Role
You are teamwork_worker (`worker_m1`).
Working directory: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Context & Inputs
You must read:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_1\handoff.md` and `analysis.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_2\handoff.md` and `analysis.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m1_3\handoff.md` and `analysis.md`

## Scope of Work (Milestone M1)
1. **Asset Backup, Legacy Wipe & Restoration**:
   - Follow `explorer_m1_1\analysis.md`.
   - Copy `backend/audio/assets/jarvis_ref.wav` to `_safe_assets/jarvis_ref.wav` and verify SHA256: `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73` (size 353,708 bytes).
   - Cleanly wipe the 24 legacy backend files, `__pycache__` dirs, obsolete `apps/`, `services/`, root `requirements.txt`, `test.cjs`, `JARVIS_AI_Prototype_Showcase.pdf`, and legacy doc files (`docs/ARCHITECTURE_DECISION.md`, `docs/SECURITY_MODEL.md`, `docs/SKILL_AUTHORING.md`).
   - Explicitly PRESERVE: `native_core/jarvis_native_fallback.py`, `PROJECT.md`, `TEST_INFRA.md`.
   - Create `backend/voice/assets/` and restore `jarvis_ref.wav`.
   - Verify SHA256 matches `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`.
   - Cleanly remove `_safe_assets/`.

2. **Directory Tree & Package Initialization**:
   - Create the 10 target `backend/` packages with `__init__.py`:
     `agents/`, `memory/`, `skills/`, `core/`, `engine/`, `security/`, `voice/`, `automation/`, `senses/`, `hardware/`.
   - Create root `backend/__init__.py`.

3. **Governance Rules & Markdown Profiles**:
   - Follow `explorer_m1_2\analysis.md`.
   - Author `.antigravity/rules.md` and `.agent/rules/rules.md` with identical SHA256 hashes containing Laws 1–4.
   - Author agent profiles: `backend/agents/planner.md`, `architect.md`, `security_auditor.md`.
   - Author memory profiles: `backend/memory/SOUL.md`, `USER.md`, `MEMORY.md`.
   - Author runtime skills: `backend/skills/desktop_control.md`, `browser_background.md`, `deep_research.md`, `document_reader.md`, `vision_biometrics_gestures.md`, `mobile_adb_control.md`.

4. **UI Visualizer Tuning**:
   - Follow `explorer_m1_3\analysis.md`.
   - Create `src/components/widgets/arc-reactor.tsx` exporting `JARVIS_LIGHTING_CONFIG` and `<ArcReactor />` with delta-time physics and exponential damping.
   - Update `src/components/dashboard/sphere.tsx` to import `JARVIS_LIGHTING_CONFIG` and `ArcReactor`, retuning the particle sphere and glow to the canonical golden-amber palette while composing `<ArcReactor overlayMode />`.
   - Ensure NO other UI files are visually modified (100% UI immutability).

## Verification Requirements
You MUST run the following commands and include full command outputs in your `handoff.md`:
1. Verify `backend/voice/assets/jarvis_ref.wav` SHA-256 and byte length.
2. Verify `_safe_assets` does not exist.
3. Verify all 10 backend subdirectories and `__init__.py` exist.
4. Verify SHA256 match of `.antigravity/rules.md` and `.agent/rules/rules.md`.
5. Verify all agent, memory, and skill profiles exist.
6. Run `npm run typecheck` (`tsc -p . --noEmit && tsc -p tsconfig.electron.json --noEmit && tsc -p tsconfig.e2e.json --noEmit`) and verify exit code 0.
7. Verify git status to confirm only intended files were modified.

Write your report to `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1\handoff.md` and notify parent.

## 2026-11-10T08:34:30Z
Read e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1\DISPATCH.md and follow all instructions strictly. Working directory: e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\worker_m1. Implement Milestone M1, run all verification commands, write handoff.md, and send completion message to parent.
