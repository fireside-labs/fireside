# Valkyrie Gate Poller — watches full pipeline, waits for Heimdall's audit gate
$GatesDir = "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates"
$MaxWaitMinutes = 30
$PollSeconds = 15
$Elapsed = 0

Write-Host ""
Write-Host "[Valkyrie] Polling every ${PollSeconds}s (timeout: ${MaxWaitMinutes}m)..." -ForegroundColor Magenta
Write-Host ""

while ($true) {
    $thor     = if (Test-Path "$GatesDir\gate_thor.md")     { "YES" } else { "..." }
    $freya    = if (Test-Path "$GatesDir\gate_freya.md")    { "YES" } else { "..." }
    $heimdall = if (Test-Path "$GatesDir\gate_heimdall.md") { "YES" } else { "..." }

    $time = Get-Date -Format "HH:mm:ss"

    if (Test-Path "$GatesDir\gate_heimdall.md") {
        Write-Host "[Valkyrie] $time  Thor: $thor | Freya: $freya | Heimdall: $heimdall" -ForegroundColor Green
        Write-Host ""
        Write-Host "[Valkyrie] Heimdall audit passed! Beginning UX and business review..." -ForegroundColor Green
        exit 0
    }

    Write-Host "[Valkyrie] $time  Thor: $thor | Freya: $freya | Heimdall: $heimdall"

    Start-Sleep -Seconds $PollSeconds
    $Elapsed += $PollSeconds

    if ($Elapsed -ge ($MaxWaitMinutes * 60)) {
        Write-Host ""
        Write-Host "[Valkyrie] TIMEOUT after ${MaxWaitMinutes} minutes." -ForegroundColor Yellow
        Write-Host "[Valkyrie] Pipeline status at timeout:" -ForegroundColor Yellow
        Write-Host "  Thor:     $thor" -ForegroundColor Yellow
        Write-Host "  Freya:    $freya" -ForegroundColor Yellow
        Write-Host "  Heimdall: $heimdall" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "[Valkyrie] Check which upstream agent hasn't dropped their gate." -ForegroundColor Yellow
        exit 1
    }
}
