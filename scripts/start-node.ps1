# start-node.ps1 -- Full mesh node startup: Ollama -> OpenClaw gateway -> Bifrost
# Launches all three in the correct order with health checks between each step.
# Safe to run at any time -- skips anything already running.
#
# Usage:  .\scripts\start-node.ps1
#         .\scripts\start-node.ps1 -SkipOllama   (if Ollama is managed separately)
#
# All three services stay running in background windows after this script exits.

param(
    [switch]$SkipOllama
)

$ErrorActionPreference = "Stop"
$BIFROST_PORT  = 8765
$GATEWAY_PORT  = 18789
$OLLAMA_PORT   = 11434

# Locate the bot directory relative to this script
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BOT_DIR    = Join-Path (Split-Path -Parent $SCRIPT_DIR) "bot"
$BIFROST    = Join-Path $BOT_DIR "bifrost.py"
$PYTHON     = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $PYTHON) { $PYTHON = "C:\Users\Jorda\AppData\Local\Programs\Python\Python312\python.exe" }

function Test-Port($port) {
    $result = netstat -ano 2>$null | findstr "LISTENING" | findstr ":$port "
    return [bool]$result
}

function Wait-Port($port, $name, $timeoutSec = 15) {
    $waited = 0
    while ($waited -lt $timeoutSec) {
        if (Test-Port $port) {
            Write-Host "  [OK] $name is up on port $port (${waited}s)" -ForegroundColor Green
            return $true
        }
        Start-Sleep 1
        $waited++
    }
    Write-Host "  [ERROR] $name did NOT come up on port $port within ${timeoutSec}s" -ForegroundColor Red
    return $false
}

Write-Host ""
Write-Host "=== Valhalla Mesh Node Startup ===" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Ollama ──────────────────────────────────────────────────────────
if (-not $SkipOllama) {
    Write-Host "[1/3] Ollama..." -ForegroundColor Yellow
    if (Test-Port $OLLAMA_PORT) {
        Write-Host "  [OK] Ollama already running on port $OLLAMA_PORT" -ForegroundColor Green
    } else {
        Write-Host "  Starting Ollama..." -ForegroundColor Gray
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized
        if (-not (Wait-Port $OLLAMA_PORT "Ollama" 20)) { exit 1 }
    }
} else {
    Write-Host "[1/3] Ollama -- skipped (use -SkipOllama flag)" -ForegroundColor Gray
}

# ── Step 2: OpenClaw Gateway ─────────────────────────────────────────────────
Write-Host "[2/3] OpenClaw gateway..." -ForegroundColor Yellow
if (Test-Port $GATEWAY_PORT) {
    Write-Host "  [OK] Gateway already running on port $GATEWAY_PORT" -ForegroundColor Green
} else {
    Write-Host "  Starting openclaw gateway..." -ForegroundColor Gray
    Start-Process -FilePath "openclaw" -ArgumentList "gateway" -WindowStyle Minimized
    if (-not (Wait-Port $GATEWAY_PORT "OpenClaw gateway" 15)) { exit 1 }
}

# ── Step 3: Bifrost ──────────────────────────────────────────────────────────
Write-Host "[3/3] Bifrost..." -ForegroundColor Yellow
if (Test-Port $BIFROST_PORT) {
    Write-Host "  [OK] Bifrost already running on port $BIFROST_PORT" -ForegroundColor Green
} else {
    if (-not (Test-Path $BIFROST)) {
        Write-Host "  [ERROR] bifrost.py not found at: $BIFROST" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Starting Bifrost ($BIFROST)..." -ForegroundColor Gray
    Start-Process -FilePath $PYTHON -ArgumentList $BIFROST `
        -WorkingDirectory $BOT_DIR -WindowStyle Minimized
    if (-not (Wait-Port $BIFROST_PORT "Bifrost" 20)) { exit 1 }
}

# ── All up ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Node is READY ===" -ForegroundColor Cyan
Write-Host "  Ollama:  http://localhost:$OLLAMA_PORT" -ForegroundColor White
Write-Host "  Gateway: http://localhost:$GATEWAY_PORT" -ForegroundColor White
Write-Host "  Bifrost: http://localhost:$BIFROST_PORT/health" -ForegroundColor White
Write-Host ""
