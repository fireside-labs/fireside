# start-gateway.ps1 -- One-click OpenClaw gateway recovery
# Checks if the gateway is listening on port 18789.
# If not, starts it. Safe to run at any time -- won't double-start.
#
# Usage: .\scripts\start-gateway.ps1
# Or from any dir: powershell -File <path>\scripts\start-gateway.ps1

$PORT = 18789
$GATEWAY_CMD = "openclaw"
$GATEWAY_ARG = "gateway"

Write-Host "=== OpenClaw Gateway Check ===" -ForegroundColor Cyan

# Check if already listening
$listening = netstat -ano | findstr "LISTENING" | findstr ":$PORT "
if ($listening) {
    $pidNum = ($listening -split '\s+' | Where-Object { $_ -match '^\d+$' } | Select-Object -Last 1)
    $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
    Write-Host "[OK] Gateway already running on port $PORT (PID $pidNum / $($proc.Name))" -ForegroundColor Green
    exit 0
}

Write-Host "[WARN] Gateway NOT running on port $PORT -- starting now..." -ForegroundColor Yellow

# Start gateway in background (minimized window, persistent)
Start-Process -FilePath $GATEWAY_CMD -ArgumentList $GATEWAY_ARG -WindowStyle Minimized

# Wait up to 10s for it to come up
$waited = 0
while ($waited -lt 10) {
    Start-Sleep -Seconds 1
    $waited++
    $check = netstat -ano | findstr "LISTENING" | findstr ":$PORT "
    if ($check) {
        Write-Host "[OK] Gateway is now listening on port $PORT (took ${waited}s)" -ForegroundColor Green
        exit 0
    }
}

Write-Host "[ERROR] Gateway did not start within 10 seconds. Try running manually: openclaw gateway" -ForegroundColor Red
exit 1
