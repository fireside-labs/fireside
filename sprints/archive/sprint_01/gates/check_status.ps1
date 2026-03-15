# Valhalla Sprint Pipeline — Quick Status Check (PowerShell)
# Usage: powershell -File sprints/current/gates/check_status.ps1

$GatesDir  = "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates"
$SprintFile = "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\SPRINT.md"

Write-Host ""
Write-Host "=== Valhalla Sprint Pipeline ===" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $SprintFile) {
    Get-Content $SprintFile -TotalCount 1 | Write-Host -ForegroundColor White
} else {
    Write-Host "No active sprint found. Ask Odin to run /sprint." -ForegroundColor Yellow
    exit 0
}

Write-Host "---"
Write-Host ""

# Phase 1: Build
$thor  = if (Test-Path "$GatesDir\gate_thor.md")  { "YES done" } else { "... working" }
$freya = if (Test-Path "$GatesDir\gate_freya.md") { "YES done" } else { "... working" }

Write-Host "  Phase 1 - Build:" -ForegroundColor White
Write-Host "    Thor:  $thor"
Write-Host "    Freya: $freya"

if ((Test-Path "$GatesDir\gate_thor.md") -and (Test-Path "$GatesDir\gate_freya.md")) {
    Write-Host "  [COMPLETE] Build phase done" -ForegroundColor Green
} else {
    Write-Host "  [WAITING] Build phase in progress" -ForegroundColor Yellow
}
Write-Host ""

# Phase 2: Security Audit
$heimdall = "... pending"
if (Test-Path "$GatesDir\audit_heimdall.md") { $heimdall = "[i] audit written" }
if (Test-Path "$GatesDir\gate_heimdall.md")  { $heimdall = "YES audit passed" }

Write-Host "  Phase 2 - Security Audit:" -ForegroundColor White
Write-Host "    Heimdall: $heimdall"
Write-Host ""

# Phase 3: UX Review
$valkyrie = "... pending"
if (Test-Path "$GatesDir\review_valkyrie.md") { $valkyrie = "[i] review written" }
if (Test-Path "$GatesDir\gate_valkyrie.md")   { $valkyrie = "YES review complete" }

Write-Host "  Phase 3 - UX & Business Review:" -ForegroundColor White
Write-Host "    Valkyrie: $valkyrie"
Write-Host ""

# Overall
if (Test-Path "$GatesDir\gate_valkyrie.md") {
    Write-Host ">>> Sprint complete! Ready for Odin to archive and start next sprint." -ForegroundColor Green
} else {
    Write-Host "... Sprint in progress..." -ForegroundColor Yellow
}
Write-Host ""
