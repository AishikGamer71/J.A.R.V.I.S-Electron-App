# ==============================================================================
# J.A.R.V.I.S. Desktop System — Milestone M1 Comprehensive Verification Suite
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "MILESTONE M1 VERIFICATION SUITE" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check 1: Verify backend/voice/assets/jarvis_ref.wav SHA-256 and byte length
Write-Host "`n[Check 1] Voice Reference Asset Verification:" -ForegroundColor Yellow
$refPath = "backend/voice/assets/jarvis_ref.wav"
if (Test-Path $refPath) {
    $item = Get-Item $refPath
    $hash = (Get-FileHash $refPath -Algorithm SHA256).Hash
    Write-Host "  Path: $refPath"
    Write-Host "  Length: $($item.Length) bytes (Expected: 353708)"
    Write-Host "  SHA256: $hash"
    $check1 = ($item.Length -eq 353708) -and ($hash -eq "81D2718566FA9617CFAACE564300488243D93EC0C554C7D4B7194BBED3E02D73")
    Write-Host "  Status: $(if ($check1) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check1) {'Green'} else {'Red'})
} else {
    Write-Host "  Status: FAIL (File not found)" -ForegroundColor Red
    $check1 = $false
}

# Check 2: Verify _safe_assets does not exist
Write-Host "`n[Check 2] _safe_assets Absence Verification:" -ForegroundColor Yellow
$safeExists = Test-Path "_safe_assets"
$check2 = -not $safeExists
Write-Host "  _safe_assets exists: $safeExists"
Write-Host "  Status: $(if ($check2) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check2) {'Green'} else {'Red'})

# Check 3: Verify all 10 backend subdirectories and __init__.py exist
Write-Host "`n[Check 3] Backend Packages and Init Files Verification:" -ForegroundColor Yellow
$expectedPackages = @('agents', 'memory', 'skills', 'core', 'engine', 'security', 'voice', 'automation', 'senses', 'hardware')
$check3 = $true
$rootInit = Test-Path "backend/__init__.py"
Write-Host "  backend/__init__.py: $rootInit"
if (-not $rootInit) { $check3 = $false }

foreach ($pkg in $expectedPackages) {
    $dirExists = Test-Path "backend/$pkg"
    $initExists = Test-Path "backend/$pkg/__init__.py"
    Write-Host "  backend/$pkg/ : Dir=$dirExists, __init__.py=$initExists"
    if (-not $dirExists -or -not $initExists) { $check3 = $false }
}
Write-Host "  Status: $(if ($check3) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check3) {'Green'} else {'Red'})

# Check 4: Verify SHA256 match of .antigravity/rules.md and .agent/rules/rules.md
Write-Host "`n[Check 4] Governance Rules Cryptographic Hash Matching:" -ForegroundColor Yellow
$rules1 = ".antigravity/rules.md"
$rules2 = ".agent/rules/rules.md"
if ((Test-Path $rules1) -and (Test-Path $rules2)) {
    $h1 = (Get-FileHash $rules1 -Algorithm SHA256).Hash
    $h2 = (Get-FileHash $rules2 -Algorithm SHA256).Hash
    Write-Host "  .antigravity/rules.md SHA256 : $h1"
    Write-Host "  .agent/rules/rules.md SHA256 : $h2"
    $check4 = ($h1 -eq $h2) -and ($h1.Length -eq 64)
    Write-Host "  Status: $(if ($check4) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check4) {'Green'} else {'Red'})
} else {
    Write-Host "  Status: FAIL (One or both rules files missing)" -ForegroundColor Red
    $check4 = $false
}

# Check 5: Verify all agent, memory, and skill profiles exist
Write-Host "`n[Check 5] Agent, Memory, and Skill Profiles Existence:" -ForegroundColor Yellow
$expectedProfiles = @(
    "backend/agents/planner.md",
    "backend/agents/architect.md",
    "backend/agents/security_auditor.md",
    "backend/memory/SOUL.md",
    "backend/memory/USER.md",
    "backend/memory/MEMORY.md",
    "backend/skills/desktop_control.md",
    "backend/skills/browser_background.md",
    "backend/skills/deep_research.md",
    "backend/skills/document_reader.md",
    "backend/skills/vision_biometrics_gestures.md",
    "backend/skills/mobile_adb_control.md"
)
$check5 = $true
foreach ($prof in $expectedProfiles) {
    $exists = Test-Path $prof
    $size = if ($exists) { (Get-Item $prof).Length } else { 0 }
    Write-Host "  $prof : Exists=$exists ($size bytes)"
    if (-not $exists -or $size -eq 0) { $check5 = $false }
}
Write-Host "  Status: $(if ($check5) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check5) {'Green'} else {'Red'})

# Check 6: Preserved Critical Files Check
Write-Host "`n[Check 6] Preserved Critical System Files:" -ForegroundColor Yellow
$criticalFiles = @(
    "native_core/jarvis_native_fallback.py",
    "PROJECT.md",
    "TEST_INFRA.md"
)
$check6 = $true
foreach ($crit in $criticalFiles) {
    $exists = Test-Path $crit
    Write-Host "  $crit : Exists=$exists"
    if (-not $exists) { $check6 = $false }
}
Write-Host "  Status: $(if ($check6) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check6) {'Green'} else {'Red'})

# Check 7: UI Visualizer Files Check
Write-Host "`n[Check 7] UI Visualizer Files Check:" -ForegroundColor Yellow
$arcExists = Test-Path "src/components/widgets/arc-reactor.tsx"
$sphereExists = Test-Path "src/components/dashboard/sphere.tsx"
Write-Host "  src/components/widgets/arc-reactor.tsx : Exists=$arcExists"
Write-Host "  src/components/dashboard/sphere.tsx    : Exists=$sphereExists"
$check7 = $arcExists -and $sphereExists
Write-Host "  Status: $(if ($check7) {'PASS'} else {'FAIL'})" -ForegroundColor $(if ($check7) {'Green'} else {'Red'})

Write-Host "`n======================================================================" -ForegroundColor Cyan
$overall = $check1 -and $check2 -and $check3 -and $check4 -and $check5 -and $check6 -and $check7
if ($overall) {
    Write-Host "OVERALL RESULT: ALL MILESTONE M1 INTEGRITY CHECKS PASSED!" -ForegroundColor Green
} else {
    Write-Host "OVERALL RESULT: ONE OR MORE CHECKS FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "======================================================================" -ForegroundColor Cyan
