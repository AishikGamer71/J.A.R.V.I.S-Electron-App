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
