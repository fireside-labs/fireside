# ============================================================================
# Valhalla Mesh V2 — Windows Installer (PowerShell)
#
# Usage:
#   irm https://get.valhalla.ai/win | iex
#
# What it does:
#   1. Detect Windows version + GPU
#   2. Install Python 3.12 if needed (winget)
#   3. Install Node.js 20 if needed (winget)
#   4. Clone repo
#   5. Install dependencies
#   6. Generate default config
#   7. Start Valhalla
# ============================================================================

$ErrorActionPreference = "Stop"

# Colors
function Write-Info($msg)    { Write-Host "  i  $msg" -ForegroundColor Cyan }
function Write-Ok($msg)      { Write-Host "  ✓  $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "  !  $msg" -ForegroundColor Yellow }
function Write-Fail($msg)    { Write-Host "  ✗  $msg" -ForegroundColor Red; exit 1 }

$VALHALLA_DIR = "$env:USERPROFILE\valhalla-mesh-v2"
$REPO_URL = "https://github.com/openclaw/valhalla-mesh-v2.git"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "  ⚡ Valhalla Mesh V2 Installer (Windows)" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "     Your personal AI mesh, one click away." -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Detect GPU
# ---------------------------------------------------------------------------

$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
Write-Info "GPU: $gpu"

$hasNvidia = $gpu -match "NVIDIA"
if ($hasNvidia) {
    Write-Ok "NVIDIA GPU detected — llama-server will use CUDA"
} else {
    Write-Warn "No NVIDIA GPU — will use cloud inference"
}

# ---------------------------------------------------------------------------
# 2. Python 3.10+
# ---------------------------------------------------------------------------

$python = $null
foreach ($py in @("python3.12", "python3.11", "python3.10", "python3", "python")) {
    try {
        $ver = & $py --version 2>&1
        if ($ver -match "3\.1[0-9]") {
            $python = $py
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Warn "Python 3.10+ not found. Installing via winget..."
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $python = "python3.12"
}
Write-Ok "Python: $(& $python --version)"

# ---------------------------------------------------------------------------
# 3. Node.js 18+
# ---------------------------------------------------------------------------

try {
    $nodeVer = (node --version) -replace 'v', ''
    $major = [int]($nodeVer -split '\.')[0]
    if ($major -lt 18) {
        throw "too old"
    }
    Write-Ok "Node.js: v$nodeVer"
} catch {
    Write-Warn "Node.js 18+ not found. Installing via winget..."
    winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    Write-Ok "Node.js installed"
}

# ---------------------------------------------------------------------------
# 4. Clone repo
# ---------------------------------------------------------------------------

if (Test-Path $VALHALLA_DIR) {
    Write-Info "Valhalla directory exists at $VALHALLA_DIR"
    Set-Location $VALHALLA_DIR
    git pull --ff-only 2>$null
} else {
    Write-Info "Cloning Valhalla Mesh V2..."
    git clone $REPO_URL $VALHALLA_DIR
    Set-Location $VALHALLA_DIR
}
Write-Ok "Source code ready"

# ---------------------------------------------------------------------------
# 5. Install dependencies
# ---------------------------------------------------------------------------

Write-Info "Installing Python dependencies..."
& $python -m pip install --upgrade pip -q
& $python -m pip install -r requirements.txt -q
Write-Ok "Python dependencies installed"

Write-Info "Installing dashboard dependencies..."
Set-Location dashboard
npm install --silent 2>$null
Set-Location ..
Write-Ok "Dashboard dependencies installed"

# ---------------------------------------------------------------------------
# 6. Generate default config
# ---------------------------------------------------------------------------

if (-not (Test-Path "valhalla.yaml")) {
    Write-Info "Generating default config..."
    @"
node:
  name: my-device
  role: orchestrator

models:
  providers: {}
  aliases:
    default: local/default

plugins:
  enabled:
    - model-switch
    - watchdog
    - event-bus
    - working-memory
    - pipeline
    - consumer-api
    - brain-installer

pipeline:
  git_branching: false
"@ | Out-File -FilePath "valhalla.yaml" -Encoding utf8
    Write-Ok "Default config created"
} else {
    Write-Ok "Config exists"
}

# ---------------------------------------------------------------------------
# 7. Start Valhalla
# ---------------------------------------------------------------------------

Write-Info "Starting Valhalla..."

Write-Host "   Starting Bifrost (backend)..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath $python -ArgumentList "bifrost.py"

Write-Host "   Starting Dashboard (frontend)..." -ForegroundColor Cyan
Set-Location dashboard
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev"
Set-Location ..

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "  ⚡ Valhalla is running!" -ForegroundColor Green
Write-Host ""
Write-Host "     Dashboard:  http://localhost:3000" -ForegroundColor White
Write-Host "     Backend:    http://localhost:8000" -ForegroundColor White
Write-Host ""

Start-Process "http://localhost:3000"

Write-Host "  Press Ctrl+C to stop Valhalla." -ForegroundColor Yellow
Wait-Process -Id $PID
