# Heimdall Gate Poller — watches for Thor + Freya completion
$GatesDir = "C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github\sprints\current\gates"
$MaxWaitMinutes = 30
$PollSeconds = 15
$Elapsed = 0

Write-Host ""
Write-Host "[Heimdall] Polling for Thor + Freya gates every ${PollSeconds}s (timeout: ${MaxWaitMinutes}m)..." -ForegroundColor Cyan
Write-Host ""

while ($true) {
    $thor  = if (Test-Path "$GatesDir\gate_thor.md")  { "YES" } else { "..." }
    $freya = if (Test-Path "$GatesDir\gate_freya.md") { "YES" } else { "..." }

    $time = Get-Date -Format "HH:mm:ss"

    if ((Test-Path "$GatesDir\gate_thor.md") -and (Test-Path "$GatesDir\gate_freya.md")) {
        Write-Host "[Heimdall] $time  Thor: $thor | Freya: $freya" -ForegroundColor Green
        Write-Host ""
        Write-Host "[Heimdall] Both gates found! Thor and Freya have completed their work." -ForegroundColor Green
        Write-Host "[Heimdall] Beginning security audit..." -ForegroundColor Green
        exit 0
    }

    Write-Host "[Heimdall] $time  Thor: $thor | Freya: $freya"

    Start-Sleep -Seconds $PollSeconds
    $Elapsed += $PollSeconds

    if ($Elapsed -ge ($MaxWaitMinutes * 60)) {
        Write-Host ""
        Write-Host "[Heimdall] TIMEOUT after ${MaxWaitMinutes} minutes." -ForegroundColor Yellow
        Write-Host "[Heimdall] Pipeline status at timeout:" -ForegroundColor Yellow
        Write-Host "  Thor:  $thor" -ForegroundColor Yellow
        Write-Host "  Freya: $freya" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "[Heimdall] Check which upstream agent hasn't dropped their gate." -ForegroundColor Yellow
        exit 1
    }
}
