# ============================================================================
# 🌉 Fireside Anywhere Bridge — Tailscale Setup (Windows / PowerShell)
#
# Usage:  .\scripts\setup_bridge.ps1
#
# This script:
#   1. Checks if Tailscale is already installed
#   2. Installs it via winget if missing
#   3. Authenticates with `tailscale up`
#   4. Displays the Tailscale IP for mobile app pairing
# ============================================================================

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "  ✔ $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  $msg" -ForegroundColor DarkGray }
function Write-Warn($msg) { Write-Host "  ⚠  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "`n  ✗ $msg`n" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  ◆  Fireside Anywhere Bridge Setup" -ForegroundColor DarkYellow
Write-Host "  ─────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Info "This lets Ember (your phone) reach Atlas (your PC)"
Write-Info "from anywhere — no port forwarding needed."
Write-Host ""

# ── Step 1: Check for Tailscale ──
$tsPath = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tsPath) {
    # Check common install location
    $defaultPath = "C:\Program Files\Tailscale\tailscale.exe"
    if (Test-Path $defaultPath) {
        $env:PATH += ";C:\Program Files\Tailscale"
        $tsPath = $defaultPath
    }
}

if ($tsPath) {
    Write-Ok "Tailscale is already installed"
} else {
    Write-Host "  Installing Tailscale..." -ForegroundColor White
    Write-Host ""

    # Try winget first
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
    } else {
        Write-Fail "winget not found. Install Tailscale manually: https://tailscale.com/download/windows"
    }

    # Add to PATH
    if (Test-Path "C:\Program Files\Tailscale") {
        $env:PATH += ";C:\Program Files\Tailscale"
    }

    $tsCheck = Get-Command tailscale -ErrorAction SilentlyContinue
    if (-not $tsCheck) {
        Write-Fail "Tailscale installation failed. Install manually: https://tailscale.com/download/windows"
    }
    Write-Ok "Tailscale installed"
}

# ── Step 2: Check if already connected ──
try {
    $status = tailscale status --json 2>$null | ConvertFrom-Json
    if ($status.BackendState -eq "Running") {
        Write-Ok "Tailscale is already connected"
    } else {
        throw "not connected"
    }
} catch {
    Write-Host ""
    Write-Host "  Connecting to Tailscale..." -ForegroundColor White
    Write-Info "A browser window will open for authentication."
    Write-Host ""

    # Support headless auth via environment variable
    $authKey = $env:TAILSCALE_AUTHKEY
    $hostname = "fireside-$($env:COMPUTERNAME.ToLower())"

    if ($authKey) {
        Write-Info "Using authkey from TAILSCALE_AUTHKEY environment variable"
        tailscale up --authkey=$authKey --hostname=$hostname
    } else {
        tailscale up --hostname=$hostname
    }

    Write-Ok "Tailscale connected"
}

# ── Step 3: Display connection info ──
$tsIP = "unknown"
try {
    $tsIP = (tailscale ip -4 2>$null).Trim()
} catch {}

$localIP = "unknown"
try {
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1).IPAddress
} catch {}

Write-Host ""
Write-Host "  ◆  Anywhere Bridge is Active  ◆" -ForegroundColor DarkYellow
Write-Host "  ─────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "     Local IP       " -ForegroundColor DarkGray -NoNewline
Write-Host "$localIP" -ForegroundColor White
Write-Host "     Tailscale IP   " -ForegroundColor DarkGray -NoNewline
Write-Host "$tsIP" -ForegroundColor White
Write-Host ""
Write-Info "Your mobile app will auto-detect and connect."
Write-Info "Make sure Tailscale is also installed on your phone."
Write-Host ""
Write-Info "iOS: https://apps.apple.com/app/tailscale/id1470499037"
Write-Info "Android: https://play.google.com/store/apps/details?id=com.tailscale.ipn"
Write-Host ""
