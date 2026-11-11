# Handoff Report: Milestone M1 Work Item 1 (Asset Backup & Clean Wipe Strategy)

**From:** teamwork_explorer (`explorer_m1_1`)  
**To:** Orchestrator (parent `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`) & Worker Agent  
**Date:** 2026-11-10T08:33:30Z  
**Type:** Hard Handoff (Investigation & Specification Complete)

---

## 1. Observation

1. **Voice Reference Audio Verification**:
   - Tool Command: `powershell -NoProfile -Command "Get-FileHash 'backend/audio/assets/jarvis_ref.wav' -Algorithm SHA256; (Get-Item 'backend/audio/assets/jarvis_ref.wav').Length"`
   - Result:
     - Algorithm: `SHA256`
     - Hash: `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`
     - Path: `E:\Projects\J.A.R.V.I.S Electron App\backend\audio\assets\jarvis_ref.wav`
     - Size: `353,708` bytes
     - Format: 24,000 Hz, 16-bit Mono PCM, 7.368 seconds duration.
2. **Legacy `backend/` Inventory (24 Files Total, Excluding `jarvis_ref.wav`)**:
   - `backend/__init__.py`
   - `backend/config.py`
   - `backend/main.py`
   - `backend/requirements.txt`
   - `backend/test_backend.py`
   - `backend/test_e2e_ws.py`
   - `backend/audio/omnivoice_tts.py`
   - `backend/audio/voice_ears.py`
   - `backend/automation/desktop_controller.py`
   - `backend/automation/s3/agent_s3.py`
   - `backend/automation/s3/common_utils.py`
   - `backend/automation/s3/grounding.py`
   - `backend/core/agent_loop.py`
   - `backend/core/context_compressor.py`
   - `backend/core/planner.py`
   - `backend/core/skill_and_cron.py`
   - `backend/core/tool_registry.py`
   - `backend/engine/inference_router.py`
   - `backend/hardware/power_guardian.py`
   - `backend/memory/instinct_learner.py`
   - `backend/memory/knowledge_rag.py`
   - `backend/memory/state_store.py`
   - `backend/security/agent_shield.py`
   - `backend/skills/desktop_assistant.md`
   - Plus associated `__pycache__` directories in each subdirectory.
3. **Auxiliary Legacy Directories & Stubs**:
   - Command: `Test-Path 'apps', 'services', 'native_core', 'requirements.txt', 'test.cjs', 'JARVIS_AI_Prototype_Showcase.pdf'`
   - Result: All return `True`.
   - `apps/` contains obsolete `apps/core-service/` with legacy tests and `.venv`.
   - `services/` contains obsolete `services/voice-service/` with legacy tests and `.venv`.
   - `requirements.txt` (root), `test.cjs` (root), `JARVIS_AI_Prototype_Showcase.pdf` (root, 19.8 MB) are legacy stubs.
   - `native_core/jarvis_native_fallback.py` is present and active (509 lines of Win32 ctypes C-ABI bridge).
4. **Documentation Markdown Files Status**:
   - Present: `README.md`, `.agent/rules/rules.md`, `.antigravity/rules.md`, `docs/ARCHITECTURE_DECISION.md`, `docs/SECURITY_MODEL.md`, `docs/SKILL_AUTHORING.md`.
   - Preserved Project Management & Test Files: `PROJECT.md` and `TEST_INFRA.md`.
5. **Team Coordination Files**:
   - `explorer_m1_2` delivered `handoff.md` and `analysis.md` specifying Work Items 2–4 (10 backend directories, governance rules, 3 agent profiles, 3 memory profiles, 6 skill profiles).
   - `explorer_m1_3` delivered `handoff.md` and `analysis.md` specifying Work Item 5 (`arc-reactor.tsx` and sphere golden-amber tuning).

---

## 2. Logic Chain

1. **From Observation 1**: `backend/audio/assets/jarvis_ref.wav` is an irreplaceable binary asset required for OmniVoice zero-shot voice cloning. Any script wiping legacy code must guarantee atomic safety by copying it to `_safe_assets/jarvis_ref.wav` and verifying its SHA256 (`81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`) and size (`353,708` bytes) before any deletion is attempted.
2. **From Observation 2 & 3**: All 24 backend Python files, `__pycache__` directories, auxiliary `apps/`, `services/`, root `requirements.txt`, `test.cjs`, and `JARVIS_AI_Prototype_Showcase.pdf` represent outdated monolith/stubs that conflict with the clean multi-environment architecture. Wiping the entire `backend/` directory after safeguarding `jarvis_ref.wav` ensures no lingering bytecode or orphaned files survive.
3. **From Observation 3**: `native_core/jarvis_native_fallback.py` provides pure ctypes Win32 fallback logic for power management, screen capture, and emergency abort, which will be integrated in Milestones M3 and M4. Therefore, it must be explicitly preserved while removing `native_core/__init__.py` and `native_core/__pycache__/`.
4. **From Observation 4**: Legacy documentation markdown files must be wiped cleanly to allow re-authoring in Phase 2 and Phase 5. Crucially, `PROJECT.md` and `TEST_INFRA.md` are active, mission-critical specifications and must NOT be removed.
5. **From Observations 1, 2, 3, 4, 5**: Authoring a deterministic PowerShell script (`scripts/clean-wipe-assets.ps1`) with strict error handling, double SHA256 assertions, target directory creation (`backend/voice/assets/`), and verification before removing `_safe_assets/` provides an error-free, verifiable execution plan for the Worker agent.

---

## 3. Caveats

- **Read-Only Scope**: In strict accordance with the explorer archetype, no file modifications or deletions were performed during this investigation.
- **File Locks**: Before executing the wipe, the Worker should ensure that no Python background processes, Electron processes, or IDE debuggers have open handles to files inside `backend/` or `services/`.
- **Git State**: Deleting legacy files will reflect in `git status`. The Worker should stage these changes cleanly as part of Milestone M1.

---

## 4. Conclusion

Milestone M1 Work Item 1 is fully investigated and ready for execution.
1. The Worker agent should create and run `scripts/clean-wipe-assets.ps1` as specified in `analysis.md`.
2. The script will:
   - Verify `jarvis_ref.wav` (size `353,708`, SHA-256 `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`).
   - Copy to `_safe_assets/jarvis_ref.wav` and re-verify hash.
   - Cleanly wipe `backend/`, `apps/`, `services/`, root stubs, and legacy docs.
   - Create `backend/voice/assets/` and restore `jarvis_ref.wav`.
   - Verify restored hash matches `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`.
   - Remove `_safe_assets/`.
3. Following this, the Worker can seamlessly execute Work Items 2–4 (`explorer_m1_2`) and Work Item 5 (`explorer_m1_3`).

---

## 5. Verification Method

To independently verify the successful execution by the Worker:

1. **Restored Asset Existence & Cryptographic Parity**:
   ```powershell
   Get-FileHash -Path "backend/voice/assets/jarvis_ref.wav" -Algorithm SHA256
   (Get-Item "backend/voice/assets/jarvis_ref.wav").Length
   ```
   - Must output Hash: `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`
   - Must output Length: `353708`

2. **Temporary Folder Removal**:
   ```powershell
   Test-Path -Path "_safe_assets"
   ```
   - Must return: `False`

3. **Absence of Legacy Backend Files & Stubs**:
   ```powershell
   Test-Path -Path "backend/audio/omnivoice_tts.py", "apps", "services", "requirements.txt", "test.cjs"
   ```
   - All must return: `False`

4. **Preservation of Critical Project Files**:
   ```powershell
   Test-Path -Path "native_core/jarvis_native_fallback.py", "PROJECT.md", "TEST_INFRA.md"
   ```
   - All must return: `True`
