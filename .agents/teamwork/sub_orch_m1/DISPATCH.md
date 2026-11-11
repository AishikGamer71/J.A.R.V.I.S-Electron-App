# DISPATCH: Milestone M1 Sub-Orchestrator

## Identity & Role
You are the Sub-Orchestrator for Milestone M1 (Workspace Governance, Rules & UI Visualizer Tuning).
Your working directory is: `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\sub_orch_m1`
Your parent orchestrator conversation ID is: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`.

## Scope & Work Items (Milestone M1)
1. **Asset Backup & Clean Wipe**:
   - Safely copy `backend/audio/assets/jarvis_ref.wav` to `_safe_assets/jarvis_ref.wav` and verify its SHA-256 hash (`81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`).
   - Cleanly wipe the 24 legacy backend files and stubs, obsolete doc files per Phase 1.2–1.3.
   - Restore reference voice prompt to `backend/voice/assets/jarvis_ref.wav`.
2. **Directory Tree**:
   - Establish target `backend/` directory structure: `agents/`, `memory/`, `skills/`, `core/`, `engine/`, `security/`, `voice/`, `automation/`, `senses/`, `hardware/`.
3. **Workspace Governance Rules**:
   - Author `.antigravity/rules.md` and `.agent/rules/rules.md` establishing:
     - Law 1: UI Immutability (zero visual edits outside arc-reactor tuning).
     - Law 2: 3-Tier Action Routing.
     - Law 3: Single Camera/Mic Ownership via SPMC CameraHub and AudioPipeline.
     - Law 4: ECC Hook Enforcement on all tool execution.
4. **Agent, Memory & Skill Profiles**:
   - Author agent profiles (`backend/agents/planner.md`, `architect.md`, `security_auditor.md`).
   - Author memory profiles (`backend/memory/SOUL.md`, `USER.md`, `MEMORY.md`).
   - Author runtime skills (`backend/skills/desktop_control.md`, `browser_background.md`, `deep_research.md`, `document_reader.md`, `vision_biometrics_gestures.md`, `mobile_adb_control.md`).
5. **UI Visualizer Tuning**:
   - Create `src/components/widgets/arc-reactor.tsx` with `JARVIS_LIGHTING_CONFIG` (balanced golden-amber palette, dark bronze outer ring, warm silver-gold inner core) and delta-time animation loop with exponential damping per Section 6.6 of master prompt.
   - Ensure clean export/bridge with dashboard so the holographic neural visualizer is active without disrupting existing React/TypeScript/Electron UI.

## Execution Rules
Follow the standard orchestrator procedure: Assess -> Decompose or run iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor -> Gate).
Strictly require Workers to write genuine implementations (no cheating, no dummy stubs).
Enforce clean gates with passing reviews and CLEAN audit.
Keep `SCOPE.md` updated and report completion to parent when M1 gate passes.

Reference materials:
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\ORIGINAL_REQUEST.md`
- `e:\Projects\J.A.R.V.I.S Electron App\PROJECT.md`
- `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\spec_miner_survey_1\spec_findings.md`
