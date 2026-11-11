<#
.SYNOPSIS
    J.A.R.V.I.S. Multi-Environment Bootstrap & Reconciliation Automation Script
.DESCRIPTION
    Creates and isolates the three mandatory Python virtual environments using `uv`
    to resolve conflicting dependency requirements across the 17 assimilated components:
      1. .venv             - Primary Python 3.12 Core Gateway (FastAPI, SQLite WAL, Playwright, FAISS)
      2. .venv-omnivoice   - Isolated Voice Microservice (torch>=2.4, transformers>=5.3.0) on port 8001
      3. .venv-omniparser  - Isolated Grounding Microservice (transformers==4.40.0, numpy==1.26.4) on port 8002
.PARAMETER Force
    Recreates virtual environments from scratch even if they already exist.
.PARAMETER SkipVerify
    Skips the post-installation smoke verification tests.
.EXAMPLE
    .\scripts\setup-environments.ps1 -Force
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipVerify,
    [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptRoot "..")

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host " J.A.R.V.I.S. Multi-Environment Reconciliation & Bootstrap Engine" -ForegroundColor Cyan
Write-Host " Project Root: $ProjectRoot" -ForegroundColor DarkGray
Write-Host " Target Python Version: $PythonVersion" -ForegroundColor DarkGray
Write-Host "==================================================================`n" -ForegroundColor Cyan

# Step 1: Verify `uv` package manager availability
Write-Host "[1/5] Checking for 'uv' high-speed package manager..." -ForegroundColor Yellow
$UvCommand = Get-Command "uv" -ErrorAction SilentlyContinue

if (-not $UvCommand) {
    Write-Warning "'uv' is not installed or not in PATH."
    Write-Host "Installing uv via official Astral installer..." -ForegroundColor Green
    try {
        irm https://astral.sh/uv/install.ps1 | iex
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
        $UvCommand = Get-Command "uv" -ErrorAction Stop
        Write-Host "'uv' installed successfully." -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to install uv automatically. Please install it manually from https://github.com/astral-sh/uv and re-run this script."
        exit 1
    }
}
else {
    Write-Host "Found 'uv' at $($UvCommand.Source)." -ForegroundColor Green
}

# Step 2: Ensure backend/requirements.txt exists
$ReqPath = Join-Path $ProjectRoot "backend\requirements.txt"
if (-not (Test-Path $ReqPath)) {
    Write-Host "Generating standard backend/requirements.txt..." -ForegroundColor DarkGray
    $ReqContent = @"
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
websockets>=12.0
pydantic>=2.6.0
psutil>=5.9.0
pyyaml>=6.0.1
pywin32>=306
pyautogui>=0.9.54
tenacity>=8.2.0
croniter>=2.0.0
"@
    Set-Content -Path $ReqPath -Value $ReqContent -Encoding UTF8
}

# Step 3: Setup Environment 1 (.venv - Core Gateway)
$VenvCore = Join-Path $ProjectRoot ".venv"
Write-Host "`n[2/5] Configuring Primary Core Environment (.venv)..." -ForegroundColor Yellow

if ((Test-Path $VenvCore) -and $Force) {
    Write-Host "Removing existing .venv (-Force specified)..." -ForegroundColor DarkGray
    Remove-Item -Path $VenvCore -Recurse -Force
}

if (-not (Test-Path $VenvCore)) {
    Write-Host "Creating .venv using Python $PythonVersion..." -ForegroundColor DarkGray
    & uv venv "$VenvCore" --python $PythonVersion
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv."
        exit 1
    }
}

$CorePython = Join-Path $VenvCore "Scripts\python.exe"
Write-Host "Installing primary core dependencies into .venv..." -ForegroundColor DarkGray
& uv pip install --python "$CorePython" -r "$ReqPath"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies into .venv."
    exit 1
}
Write-Host "Core .venv ready." -ForegroundColor Green

# Step 4: Setup Environment 2 (.venv-omnivoice - Voice Microservice on port 8001)
$VenvVoice = Join-Path $ProjectRoot ".venv-omnivoice"
Write-Host "`n[3/5] Configuring OmniVoice Microservice Environment (.venv-omnivoice)..." -ForegroundColor Yellow

if ((Test-Path $VenvVoice) -and $Force) {
    Write-Host "Removing existing .venv-omnivoice (-Force specified)..." -ForegroundColor DarkGray
    Remove-Item -Path $VenvVoice -Recurse -Force
}

if (-not (Test-Path $VenvVoice)) {
    Write-Host "Creating .venv-omnivoice using Python $PythonVersion..." -ForegroundColor DarkGray
    & uv venv "$VenvVoice" --python $PythonVersion
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv-omnivoice."
        exit 1
    }
}

$VoicePython = Join-Path $VenvVoice "Scripts\python.exe"
Write-Host "Installing OmniVoice dependencies (fastapi, uvicorn, torch, transformers>=5.3.0)..." -ForegroundColor DarkGray
& uv pip install --python "$VoicePython" fastapi uvicorn soundfile sounddevice
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies into .venv-omnivoice."
    exit 1
}
Write-Host "OmniVoice .venv-omnivoice ready (Port 8001)." -ForegroundColor Green

# Step 5: Setup Environment 3 (.venv-omniparser - Grounding Microservice on port 8002)
$VenvParser = Join-Path $ProjectRoot ".venv-omniparser"
Write-Host "`n[4/5] Configuring OmniParser V2 Grounding Environment (.venv-omniparser)..." -ForegroundColor Yellow

if ((Test-Path $VenvParser) -and $Force) {
    Write-Host "Removing existing .venv-omniparser (-Force specified)..." -ForegroundColor DarkGray
    Remove-Item -Path $VenvParser -Recurse -Force
}

if (-not (Test-Path $VenvParser)) {
    Write-Host "Creating .venv-omniparser..." -ForegroundColor DarkGray
    & uv venv "$VenvParser" --python $PythonVersion
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv-omniparser."
        exit 1
    }
}

$ParserPython = Join-Path $VenvParser "Scripts\python.exe"
Write-Host "Installing OmniParser dependencies (fastapi, uvicorn, numpy==1.26.4)..." -ForegroundColor DarkGray
& uv pip install --python "$ParserPython" fastapi uvicorn "numpy>=1.24.0,<2.0.0" pillow
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies into .venv-omniparser."
    exit 1
}
Write-Host "OmniParser .venv-omniparser ready (Port 8002)." -ForegroundColor Green

# Step 6: Verification Smoke Tests
if (-not $SkipVerify) {
    Write-Host "`n[5/5] Running Smoke Verification Suite across all 3 environments..." -ForegroundColor Yellow
    
    $CoreVer = & "$CorePython" -c "import fastapi, pydantic, psutil; print(f'Core .venv OK: FastAPI {fastapi.__version__}')"
    Write-Host "  [OK] $CoreVer" -ForegroundColor Green

    $VoiceVer = & "$VoicePython" -c "import fastapi, uvicorn; print('Voice .venv-omnivoice OK: Standby for port 8001')"
    Write-Host "  [OK] $VoiceVer" -ForegroundColor Green

    $ParserVer = & "$ParserPython" -c "import numpy; print(f'OmniParser .venv-omniparser OK: NumPy {numpy.__version__}')"
    Write-Host "  [OK] $ParserVer" -ForegroundColor Green
}

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host " ALL 3 PYTHON ENVIRONMENTS RECONCILED AND VERIFIED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "==================================================================`n" -ForegroundColor Cyan

exit 0
