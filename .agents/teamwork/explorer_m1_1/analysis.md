# Analysis: Milestone M1 Work Item 1 (Asset Backup & Clean Wipe Strategy)

**Author:** teamwork_explorer (`explorer_m1_1`)  
**Date:** 2026-11-10T08:32:00Z  
**Task:** Fail-Safe Execution Strategy for Voice Asset Backup, Legacy Code Clean Wipe, and Target Voice Asset Restoration  
**Target Recipient:** Orchestrator (`0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`) and Worker Agent

---

## 1. Executive Summary

Milestone M1 Work Item 1 is the foundational gate for the entire J.A.R.V.I.S. Desktop System overhaul. It guarantees that the unique voice prompt asset (`jarvis_ref.wav`) is preserved with 100% cryptographic integrity, while eradicating all legacy backend files, stubs, obsolete documentation, and rogue services so that subsequent milestone assimilations operate on a clean, deterministic workspace.

### Key Audit Findings
1. **Source Asset Verified**:
   - Location: `backend/audio/assets/jarvis_ref.wav`
   - File Size: `353,708` bytes (exact)
   - SHA-256: `81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`
   - Audio Specs: RIFF WAVE 24,000 Hz, 16-bit Mono PCM, 176,832 samples, 7.368 seconds duration.
2. **Legacy Deletion Scope**:
   - Exactly **24 legacy backend files** in `backend/` across 8 subdirectories, plus multiple `__pycache__` artifacts.
   - **2 obsolete auxiliary service directories**: `apps/` (`apps/core-service/` including isolated `.venv`) and `services/` (`services/voice-service/` including isolated `.venv`).
   - **3 obsolete root files**: `requirements.txt` (root), `test.cjs`, `JARVIS_AI_Prototype_Showcase.pdf` (19.8 MB).
   - **11 legacy documentation markdown files**: `README.md`, `.agent/rules/rules.md`, `.antigravity/rules.md`, and legacy `.md` files in `docs/` (`ARCHITECTURE_DECISION.md`, `SECURITY_MODEL.md`, `SKILL_AUTHORING.md`, etc.).
3. **Protected Workspace Artifacts**:
   - `native_core/jarvis_native_fallback.py`: Critical ctypes Win32 fallback module that must be PRESERVED.
   - `PROJECT.md`: Source of truth for project milestones and features (PRESERVE).
   - `TEST_INFRA.md`: Approved E2E test infrastructure specification (PRESERVE).
   - `.agents/teamwork/`: Metadata workspace for teamwork agents (NEVER TOUCH).
   - `src/`: Untouched UI tree (NEVER TOUCH in this work item).

---

## 2. Detailed Inventory of Files to Wipe

### 2.1 The 24 Legacy Backend Files (Under `backend/`)
All files below must be completely wiped:

| # | File Path | Current Size | Role / Reason for Deletion |
|---|-----------|--------------|---------------------------|
| 1 | `backend/__init__.py` | 89 B | Stale root package initializer |
| 2 | `backend/config.py` | 3,934 B | Legacy Pydantic configuration |
| 3 | `backend/main.py` | 20,209 B | Stale monolith FastAPI server |
| 4 | `backend/requirements.txt` | 282 B | Stale dependency specification |
| 5 | `backend/test_backend.py` | 7,437 B | Legacy unit test script |
| 6 | `backend/test_e2e_ws.py` | 4,611 B | Legacy WebSocket test script |
| 7 | `backend/audio/omnivoice_tts.py` | 7,675 B | Legacy TTS wrapper |
| 8 | `backend/audio/voice_ears.py` | 2,386 B | Legacy wake word stub |
| 9 | `backend/automation/desktop_controller.py` | 5,389 B | Legacy pyautogui controller |
| 10 | `backend/automation/s3/agent_s3.py` | 2,606 B | Stale S3 runner stub |
| 11 | `backend/automation/s3/common_utils.py` | 1,483 B | Stale S3 utility code |
| 12 | `backend/automation/s3/grounding.py` | 5,738 B | Stale bounding box code |
| 13 | `backend/core/agent_loop.py` | 12,999 B | Legacy Gemini loop |
| 14 | `backend/core/context_compressor.py` | 2,944 B | Legacy naive compressor |
| 15 | `backend/core/planner.py` | 3,873 B | Legacy planner stub |
| 16 | `backend/core/skill_and_cron.py` | 7,109 B | Legacy cron loop |
| 17 | `backend/core/tool_registry.py` | 3,514 B | Legacy tool registry |
| 18 | `backend/engine/inference_router.py` | 14,948 B | Legacy router |
| 19 | `backend/hardware/power_guardian.py` | 4,098 B | Legacy power check |
| 20 | `backend/memory/instinct_learner.py` | 6,095 B | Legacy instinct store |
| 21 | `backend/memory/knowledge_rag.py` | 5,818 B | Legacy TF-IDF RAG |
| 22 | `backend/memory/state_store.py` | 8,920 B | Legacy state store |
| 23 | `backend/security/agent_shield.py` | 3,699 B | Legacy regex shield |
| 24 | `backend/skills/desktop_assistant.md` | 344 B | Legacy skill stub |

*Note*: Wiping the `backend/` directory after safeguarding `jarvis_ref.wav` eradicates all 24 files as well as all associated `__pycache__` directories.

### 2.2 Auxiliary Legacy Directories & Stubs
- `apps/`: Obsolete monorepo attempt (`apps/core-service/` containing legacy tests, `uv.lock`, `.venv`).
- `services/`: Obsolete decoupled service attempt (`services/voice-service/` containing unlinked audio code, `.venv`).
- `requirements.txt` (root level, 473 B): Replaced by isolated `uv` environments in Milestone M5.
- `test.cjs` (root level, 488 B): Unused legacy test stub.
- `JARVIS_AI_Prototype_Showcase.pdf` (root level, 19.8 MB): Stale binary presentation artifact.
- `native_core/__init__.py` and `native_core/__pycache__/`: Legacy package init to clean; **`native_core/jarvis_native_fallback.py` MUST be retained**.

### 2.3 Legacy Documentation Markdown Files
The master prompt specifies wiping 11 legacy `.md` files to allow clean re-authoring in Phase 2 and Phase 5:
- `README.md` (root)
- `.agent/rules/rules.md`
- `.antigravity/rules.md`
- `backend/skills/desktop_assistant.md` (wiped with `backend/`)
- `docs/ARCHITECTURE_DECISION.md`
- `docs/SECURITY_MODEL.md`
- `docs/SKILL_AUTHORING.md`
- `docs/ARC_REACTOR_VISUALIZER.md` (wipe if present)
- `docs/HERMES_MIGRATION.md` (wipe if present)
- `docs/JARVIS_SHOWCASE_SCRIPT.md` (wipe if present)
- `docs/PYTHON_BACKEND.md` (wipe if present)
- `docs/SWARM_ARCHITECTURE.md` (wipe if present)
- `docs/SYSTEM_DIAGNOSTIC.md` (wipe if present)
- `docs/SYSTEM_METRICS.md` (wipe if present)

---

## 3. Recommended Worker Execution Script

To eliminate human error, quote-escaping bugs in shells, and accidental asset deletion, the Worker should execute a self-contained, fail-safe PowerShell script.

### Script Specifications:
1. **Atomic Guardrails**: Sets `$ErrorActionPreference = "Stop"` so any failure immediately halts execution.
2. **Double Checksum Verification**: Validates size (`353708`) and SHA256 (`81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73`) before copying, after backing up, and after restoring.
3. **No-Wipe Gate**: If backup copy or verification fails for any reason, the script throws an error and aborts BEFORE touching `backend/` or any documentation file.
4. **Target Structure Preparation**: Creates `backend/voice/assets/` and copies `jarvis_ref.wav` into position.
5. **Safe Cleanup**: Only removes `_safe_assets/` after confirming the restored file exists and matches the exact hash.

### Production PowerShell Code (`scripts/clean-wipe-assets.ps1`):

```powershell
# ==============================================================================
# J.A.R.V.I.S. Desktop System — Milestone M1 Work Item 1: Asset Backup & Clean Wipe
# Fail-Safe Execution Script
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=== Step 1: Pre-Execution Verification of Voice Reference Asset ===" -ForegroundColor Cyan
$sourcePath = "backend/audio/assets/jarvis_ref.wav"
$expectedHash = "81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73"
$expectedSize = 353708

if (-not (Test-Path -Path $sourcePath)) {
    throw "ABORT: Source asset does not exist at '$sourcePath'!"
}

$sourceItem = Get-Item -Path $sourcePath
if ($sourceItem.Length -ne $expectedSize) {
    throw "ABORT: Source asset size mismatch! Found $($sourceItem.Length), expected $expectedSize bytes."
}

$sourceHash = (Get-FileHash -Path $sourcePath -Algorithm SHA256).Hash
if ($sourceHash -ne $expectedHash) {
    throw "ABORT: Source asset SHA256 mismatch! Found $sourceHash, expected $expectedHash."
}
Write-Host "Source asset verified: Size=$($sourceItem.Length) bytes, SHA256=$sourceHash" -ForegroundColor Green

Write-Host "`n=== Step 2: Backup Voice Asset to _safe_assets/ ===" -ForegroundColor Cyan
$safeDir = "_safe_assets"
if (-not (Test-Path -Path $safeDir)) {
    New-Item -ItemType Directory -Path $safeDir -Force | Out-Null
}

$safePath = Join-Path $safeDir "jarvis_ref.wav"
Copy-Item -Path $sourcePath -Destination $safePath -Force

if (-not (Test-Path -Path $safePath)) {
    throw "ABORT: Backup copy failed, '$safePath' not found!"
}

$safeItem = Get-Item -Path $safePath
if ($safeItem.Length -ne $expectedSize) {
    throw "ABORT: Backup file size mismatch! Found $($safeItem.Length), expected $expectedSize bytes."
}

$safeHash = (Get-FileHash -Path $safePath -Algorithm SHA256).Hash
if ($safeHash -ne $expectedHash) {
    throw "ABORT: Backup SHA256 checksum mismatch! Found $safeHash, expected $expectedHash."
}
Write-Host "Backup asset verified: Size=$($safeItem.Length) bytes, SHA256=$safeHash" -ForegroundColor Green

Write-Host "`n=== Step 3: Clean Wipe of Legacy Backend Files & Stubs ===" -ForegroundColor Cyan
# Completely wipe backend directory (including all 24 legacy files and __pycache__ folders)
if (Test-Path -Path "backend") {
    Remove-Item -Path "backend" -Recurse -Force
    Write-Host "Deleted legacy backend/ directory." -ForegroundColor Yellow
}

# Wipe auxiliary legacy service and stub directories
$legacyDirsToWipe = @("apps", "services")
foreach ($dir in $legacyDirsToWipe) {
    if (Test-Path -Path $dir) {
        Remove-Item -Path $dir -Recurse -Force
        Write-Host "Deleted legacy directory: $dir/" -ForegroundColor Yellow
    }
}

# Wipe auxiliary legacy root files
$legacyFilesToWipe = @("requirements.txt", "test.cjs", "JARVIS_AI_Prototype_Showcase.pdf")
foreach ($file in $legacyFilesToWipe) {
    if (Test-Path -Path $file) {
        Remove-Item -Path $file -Force
        Write-Host "Deleted legacy file: $file" -ForegroundColor Yellow
    }
}

# Clean native_core legacy package stubs while strictly preserving jarvis_native_fallback.py
if (Test-Path -Path "native_core/__init__.py") {
    Remove-Item -Path "native_core/__init__.py" -Force
    Write-Host "Deleted native_core/__init__.py" -ForegroundColor Yellow
}
if (Test-Path -Path "native_core/__pycache__") {
    Remove-Item -Path "native_core/__pycache__" -Recurse -Force
    Write-Host "Deleted native_core/__pycache__/" -ForegroundColor Yellow
}

Write-Host "`n=== Step 4: Clean Wipe of Legacy Documentation Markdown Files ===" -ForegroundColor Cyan
$legacyDocsToWipe = @(
    "README.md",
    ".agent/rules/rules.md",
    ".antigravity/rules.md",
    "docs/ARC_REACTOR_VISUALIZER.md",
    "docs/HERMES_MIGRATION.md",
    "docs/JARVIS_SHOWCASE_SCRIPT.md",
    "docs/PYTHON_BACKEND.md",
    "docs/SWARM_ARCHITECTURE.md",
    "docs/SYSTEM_DIAGNOSTIC.md",
    "docs/SYSTEM_METRICS.md",
    "docs/ARCHITECTURE_DECISION.md",
    "docs/SECURITY_MODEL.md",
    "docs/SKILL_AUTHORING.md"
)

foreach ($doc in $legacyDocsToWipe) {
    if (Test-Path -Path $doc) {
        Remove-Item -Path $doc -Force
        Write-Host "Deleted legacy doc: $doc" -ForegroundColor Yellow
    }
}

# Clean empty .agent/rules directory if empty
if ((Test-Path -Path ".agent/rules") -and ((Get-ChildItem -Path ".agent/rules" -Force).Count -eq 0)) {
    Remove-Item -Path ".agent/rules" -Force
}
if ((Test-Path -Path ".agent") -and ((Get-ChildItem -Path ".agent" -Force).Count -eq 0)) {
    Remove-Item -Path ".agent" -Force
}

Write-Host "`n=== Step 5: Restore Voice Reference Asset to Target Directory ===" -ForegroundColor Cyan
$targetDir = "backend/voice/assets"
if (-not (Test-Path -Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$targetPath = Join-Path $targetDir "jarvis_ref.wav"
Copy-Item -Path $safePath -Destination $targetPath -Force

if (-not (Test-Path -Path $targetPath)) {
    throw "ABORT: Target restoration failed, '$targetPath' not found!"
}

$targetItem = Get-Item -Path $targetPath
if ($targetItem.Length -ne $expectedSize) {
    throw "ABORT: Restored file size mismatch! Found $($targetItem.Length), expected $expectedSize bytes."
}

$targetHash = (Get-FileHash -Path $targetPath -Algorithm SHA256).Hash
if ($targetHash -ne $expectedHash) {
    throw "ABORT: Restored SHA256 checksum mismatch! Found $targetHash, expected $expectedHash."
}
Write-Host "Restored asset verified at '$targetPath': Size=$($targetItem.Length) bytes, SHA256=$targetHash" -ForegroundColor Green

Write-Host "`n=== Step 6: Clean Up Temporary _safe_assets Directory ===" -ForegroundColor Cyan
if (Test-Path -Path $safeDir) {
    Remove-Item -Path $safeDir -Recurse -Force
    Write-Host "Removed temporary backup directory '$safeDir/'" -ForegroundColor Yellow
}

Write-Host "`n=== Final Verification Summary ===" -ForegroundColor Cyan
$finalCheck = @{
    RestoredAssetExists = (Test-Path -Path "backend/voice/assets/jarvis_ref.wav")
    SafeAssetsRemoved   = (-not (Test-Path -Path "_safe_assets"))
    LegacyBackendWiped  = (-not (Test-Path -Path "backend/audio/omnivoice_tts.py"))
    AppsWiped           = (-not (Test-Path -Path "apps"))
    ServicesWiped       = (-not (Test-Path -Path "services"))
    FallbackPreserved   = (Test-Path -Path "native_core/jarvis_native_fallback.py")
    ProjectMdPreserved  = (Test-Path -Path "PROJECT.md")
    TestInfraPreserved  = (Test-Path -Path "TEST_INFRA.md")
}

$allPassed = $true
foreach ($key in $finalCheck.Keys) {
    $status = $finalCheck[$key]
    if ($status) {
        Write-Host "  [PASS] $key" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $key" -ForegroundColor Red
        $allPassed = $false
    }
}

if (-not $allPassed) {
    throw "Verification failed! One or more checks failed."
}

Write-Host "`nSUCCESS: Milestone M1 Work Item 1 executed cleanly with zero data loss!" -ForegroundColor Green
```

---

## 4. Execution Guidance for Worker Agent

1. **Do not execute piecemeal shell one-liners**: In PowerShell, inline expressions containing quotes or `$_` can expand unexpectedly in Windows cmd/pwsh subshells. Writing the script to a `.ps1` file and running `powershell -ExecutionPolicy Bypass -File <path>` guarantees atomic, error-free execution.
2. **Sequence of Implementation**:
   - Worker writes the script above to `scripts/clean-wipe-assets.ps1`.
   - Worker runs the script.
   - Worker verifies all exit codes are 0 and checks match.
   - Once complete, Worker coordinates with Work Item 2 (directory structure, governance rules, and profiles as specified by `explorer_m1_2`) and Work Item 5 (`arc-reactor.tsx` and sphere tuning as specified by `explorer_m1_3`).

---

## 5. Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation Built into Strategy |
| :--- | :---: | :---: | :--- |
| **Asset Corruption during Copy** | Very Low | Critical | Byte-size and SHA-256 verification before deletion and after restoration. |
| **Accidental Deletion of `jarvis_ref.wav`** | Low | Catastrophic | Strict order of operations: wipe command is guarded and only executes after backup is verified. |
| **Accidental Wipe of Active Project Files (`PROJECT.md`, `TEST_INFRA.md`)** | Low | High | Explicit exclusion list; script targets only specific legacy files and checks `PROJECT.md` / `TEST_INFRA.md` existence at the end. |
| **Leftover `.pyc` / `__pycache__` clutter** | Medium | Medium | Wiping the entire `backend/` directory guarantees 100% eradication of compiled bytecode caches. |
| **Incomplete Wipe of Auxiliary Services** | Low | Medium | Explicitly targeting `apps/` and `services/` prevents confusion with new multi-env layout. |
