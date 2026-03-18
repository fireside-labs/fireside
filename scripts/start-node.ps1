# start-node.ps1 -- Full mesh node startup: Bifrost (with auto brain manager)
# Bifrost now auto-starts llama-server via brain_manager — no separate OpenClaw
# gateway needed. This script just ensures Bifrost is running with health checks.
#
# Usage:  .\scripts\start-node.ps1
#
# Bifrost stays running in a background window after this script exits.
# llama-server is managed internally by Bifrost's brain_manager.

param(
    [switch]$SkipBrainAutoStart
)

$ErrorActionPreference = "Stop"
$BIFROST_PORT     = 8765

# Locate the project directory relative to this script
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$BIFROST    = Join-Path $PROJECT_DIR "bifrost.py"
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

# ── Step 1: Bifrost (auto-starts llama-server via brain_manager) ─────────────
Write-Host "[1/1] Bifrost..." -ForegroundColor Yellow
if (Test-Port $BIFROST_PORT) {
    Write-Host "  [OK] Bifrost already running on port $BIFROST_PORT" -ForegroundColor Green
} else {
    if (-not (Test-Path $BIFROST)) {
        Write-Host "  [ERROR] bifrost.py not found at: $BIFROST" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Loading persistent env vars (NVIDIA_API_KEY etc)..." -ForegroundColor Gray
    # Explicitly pull User-scope env vars from registry so they're inherited by Bifrost
    # even when this script is launched from Task Scheduler or a non-interactive shell.
    $userEnvKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment")
    if ($userEnvKey) {
        foreach ($name in $userEnvKey.GetValueNames()) {
            $val = $userEnvKey.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            if ($val -ne $null) { [System.Environment]::SetEnvironmentVariable($name, $val, "Process") }
        }
        $userEnvKey.Close()
    }
    Write-Host "  Starting Bifrost ($BIFROST)..." -ForegroundColor Gray
    Write-Host "  (brain_manager will auto-start llama-server if a model is configured)" -ForegroundColor DarkGray
    Start-Process -FilePath $PYTHON -ArgumentList $BIFROST `
        -WorkingDirectory $PROJECT_DIR -WindowStyle Minimized
    if (-not (Wait-Port $BIFROST_PORT "Bifrost" 20)) { exit 1 }
}

# ── All up ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Node is READY ===" -ForegroundColor Cyan
Write-Host "  Bifrost:      http://localhost:$BIFROST_PORT/health" -ForegroundColor White
Write-Host "  Brain Lab:    http://localhost:$BIFROST_PORT/api/v1/brains/status" -ForegroundColor White
Write-Host "  Dashboard:    http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "  Brain manager auto-starts llama-server when a model is installed." -ForegroundColor DarkGray
Write-Host "  Use the Brain Lab (http://localhost:3000/brains) to download & equip models." -ForegroundColor DarkGray
Write-Host ""
