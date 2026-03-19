# circuit-sweep.ps1 — Find reasoning circuits in your model
# Uses one GPU (CUDA:3 by default) so it won't interfere with your running llama-server
#
# Usage: .\scripts\circuit-sweep.ps1 -ModelPath "C:\path\to\model.gguf"
# Results saved to: .\circuit-results\
#
# Takes 2-4 hours depending on model size. Run overnight.

param(
    [Parameter(Mandatory=$true)]
    [string]$ModelPath,

    [string]$LlamaServer = "$env:USERPROFILE\.openclaw\llama-server\llama-server.exe",

    # Use GPU index 3 (last 5090) so main server stays on GPU 0
    [int]$GpuDevice = 3,

    [int]$Port = 8099,

    # Search params: block sizes of 3 and 4, scan layers 5-30
    [string]$BlockSizes = "3,4",
    [int]$StartMin = 5,
    [int]$StartMax = 30
)

$ErrorActionPreference = "Stop"
$RESULTS_DIR = Join-Path (Split-Path -Parent $PSScriptRoot) "circuit-results"
$REPO_DIR = Join-Path $env:TEMP "llm-circuit-finder"

# Step 1: Clone the repo if not already there
if (-not (Test-Path $REPO_DIR)) {
    Write-Host "[1/4] Cloning llm-circuit-finder..." -ForegroundColor Yellow
    git clone https://github.com/alainnothere/llm-circuit-finder.git $REPO_DIR
} else {
    Write-Host "[1/4] Circuit finder already cloned" -ForegroundColor Green
}

# Step 2: Install deps
Write-Host "[2/4] Installing dependencies..." -ForegroundColor Yellow
pip install gguf requests tqdm --quiet

# Step 3: Create results dir
New-Item -ItemType Directory -Path $RESULTS_DIR -Force | Out-Null

# Step 4: Run the sweep
Write-Host "[3/4] Starting circuit sweep..." -ForegroundColor Cyan
Write-Host "  Model:  $ModelPath" -ForegroundColor White
Write-Host "  GPU:    CUDA:$GpuDevice (keeping other GPUs free)" -ForegroundColor White
Write-Host "  Blocks: $BlockSizes layers" -ForegroundColor White
Write-Host "  Range:  layers $StartMin to $StartMax" -ForegroundColor White
Write-Host "  Port:   $Port" -ForegroundColor White
Write-Host ""
Write-Host "  This will take 2-4 hours. Go fix bugs." -ForegroundColor DarkGray
Write-Host ""

$sweepScript = Join-Path $REPO_DIR "sweep.py"
$resultsFile = Join-Path $RESULTS_DIR "sweep-results.jsonl"
$tmpDir = Join-Path $env:TEMP "rys-tmp"

# Build block sizes arg
$blockArgs = ($BlockSizes -split ",") | ForEach-Object { $_.Trim() }
$blockArgsStr = $blockArgs -join " "

python $sweepScript `
    --model $ModelPath `
    --llama-server $LlamaServer `
    --tmpdir $tmpDir `
    --results $resultsFile `
    --block-sizes $blockArgsStr `
    --stride 1 `
    --start-min $StartMin `
    --start-max $StartMax `
    --port $Port `
    --server-args "-ngl 99 --device CUDA$GpuDevice"

Write-Host ""
Write-Host "[4/4] Sweep complete!" -ForegroundColor Green
Write-Host "  Results: $resultsFile" -ForegroundColor White
Write-Host ""
Write-Host "  Next: review results and apply the best circuit:" -ForegroundColor Cyan
Write-Host "  python $REPO_DIR\layer_path.py $ModelPath boosted-model.gguf -p `"BEST_PATTERN_HERE`" -v" -ForegroundColor White
