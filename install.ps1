# ============================================================================
# 🔥 Fireside — Interactive Install Wizard (Windows)
#
# Usage:
#   irm getfireside.ai/install.ps1 | iex
#
# The friendliest AI installer you've ever used.
# ============================================================================

$ErrorActionPreference = "Stop"
$VERSION = "1.0.0"

# ─── Colors (ANSI) ───
$ESC   = [char]27
$RED   = "$ESC[0;31m"
$GREEN = "$ESC[0;32m"
$BLUE  = "$ESC[0;34m"
$AMBER = "$ESC[38;5;214m"
$DIM   = "$ESC[0;90m"
$BOLD  = "$ESC[1m"
$ITALIC= "$ESC[3m"
$NC    = "$ESC[0m"

$FIRESIDE_DIR = Join-Path $env:USERPROFILE ".fireside"
$VALHALLA_DIR = Join-Path $env:USERPROFILE ".valhalla"
$REPO_URL     = "https://github.com/JordanFableFur/valhalla-mesh.git"

# ─── Helpers ───
function Ok($msg)   { Write-Host "  ${GREEN}✔${NC} $msg" }
function Info($msg)  { Write-Host "  ${DIM}$msg${NC}" }
function Warn($msg)  { Write-Host "  ${AMBER}⚠${NC}  $msg" }
function Fail($msg)  { Write-Host "`n  ${RED}✗ $msg${NC}`n"; exit 1 }

function Ask-Choice {
    param([int]$Min, [int]$Max, [int]$Default)
    while ($true) {
        Write-Host -NoNewline "  ${AMBER}→${NC} "
        $val = Read-Host
        if ([string]::IsNullOrWhiteSpace($val)) { return $Default }
        $num = 0
        if ([int]::TryParse($val, [ref]$num) -and $num -ge $Min -and $num -le $Max) {
            return $num
        }
        Write-Host "  ${DIM}Hmm, that's not an option. Pick a number from ${Min}-${Max}.${NC}"
    }
}

function Progress-Bar {
    param([string]$Label, [int]$Seconds = 3)
    $width = 30
    Write-Host -NoNewline "  ${DIM}${Label}${NC} "
    for ($i = 0; $i -le $width; $i++) {
        Write-Host -NoNewline "${AMBER}█${NC}"
        Start-Sleep -Milliseconds ([int]($Seconds * 1000 / $width))
    }
    Write-Host " ${GREEN}✔${NC}"
}

# ============================================================================
# HEADER
# ============================================================================

Clear-Host
Write-Host ""
Write-Host ""
Write-Host "       ${AMBER}${BOLD}◆  W E L C O M E   T O   F I R E S I D E  ◆${NC}"
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "       ${AMBER}🔥${NC}  ${DIM}v${VERSION}${NC}"
Write-Host ""
Write-Host "       ${DIM}The AI companion that learns while you sleep.${NC}"
Write-Host "       ${DIM}This takes about 2 minutes.${NC}"
Write-Host ""
Write-Host ""
Start-Sleep -Seconds 1

# ============================================================================
# SYSTEM CHECK
# ============================================================================

Write-Host "  ${BOLD}Checking your system...${NC}"
Write-Host ""

$RAM_GB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

$GPU_NAME = "CPU only"
$GPU_VRAM = 0
try {
    $gpu = Get-CimInstance Win32_VideoController |
           Where-Object { $_.Name -match "NVIDIA|AMD|RTX|GTX|Radeon" } |
           Select-Object -First 1
    if ($gpu) {
        $GPU_NAME = $gpu.Name
        $nvSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if ($nvSmi) {
            $vram = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null |
                    Select-Object -First 1
            if ($vram) { $GPU_VRAM = [math]::Round([int]$vram / 1024) }
        }
    }
} catch {}

Ok "Windows ($([System.Environment]::OSVersion.Version.Build))"
Ok "${RAM_GB}GB RAM"
Ok "GPU: $GPU_NAME"
Write-Host ""
Start-Sleep -Milliseconds 500

# ============================================================================
# STEP 1: YOUR NAME
# ============================================================================

Write-Host "  ${BOLD}What should your companion call you?${NC}"
Write-Host "  ${DIM}(Just your first name is perfect)${NC}"
Write-Host ""
Write-Host -NoNewline "  ${AMBER}→${NC} "
$USER_NAME = Read-Host

if ([string]::IsNullOrWhiteSpace($USER_NAME)) { $USER_NAME = "Friend" }
$USER_NAME = $USER_NAME.Substring(0,1).ToUpper() + $USER_NAME.Substring(1)

Write-Host ""
Write-Host "  ${DIM}Nice to meet you, ${NC}${BOLD}${USER_NAME}${NC}${DIM}. ☀️${NC}"
Write-Host ""
Start-Sleep -Milliseconds 800

# ============================================================================
# STEP 2: PICK A BRAIN
# ============================================================================

Write-Host "  ${BOLD}Pick a brain for your AI:${NC}"
Write-Host ""

if     ($RAM_GB -ge 48) { $REC = 2 }
elseif ($RAM_GB -ge 16) { $REC = 1 }
else                    { $REC = 3 }

$r1 = if ($REC -eq 1) { "  ${GREEN}<- recommended${NC}" } else { "" }
$r2 = if ($REC -eq 2) { "  ${GREEN}<- recommended${NC}" } else { "" }
$r3 = if ($REC -eq 3) { "  ${GREEN}<- recommended${NC}" } else { "" }

Write-Host "    ${AMBER}[1]${NC} Smart & Fast   ${DIM}7B model · ~4GB download${NC}$r1"
Write-Host "    ${AMBER}[2]${NC} Deep Thinker   ${DIM}35B model · ~20GB download${NC}$r2"
Write-Host "    ${AMBER}[3]${NC} Compact        ${DIM}3B model · ~2GB download${NC}$r3"
Write-Host ""

$BRAIN_CHOICE = Ask-Choice -Min 1 -Max 3 -Default $REC

switch ($BRAIN_CHOICE) {
    2       { $BRAIN = "deep-thinker-35b"; $BRAIN_LABEL = "Deep Thinker (35B)"; $BRAIN_RAM = 24 }
    3       { $BRAIN = "compact-3b";       $BRAIN_LABEL = "Compact (3B)";       $BRAIN_RAM = 4 }
    default { $BRAIN = "smart-fast-7b";    $BRAIN_LABEL = "Smart & Fast (7B)";  $BRAIN_RAM = 8 }
}

if ($RAM_GB -lt $BRAIN_RAM) {
    Write-Host ""
    Warn "The $BRAIN_LABEL brain works best with ${BRAIN_RAM}GB+ RAM."
    Warn "You have ${RAM_GB}GB. It may run slowly."
    Write-Host ""
    Write-Host "  ${DIM}Switch to a smaller brain? (y/n)${NC}"
    Write-Host -NoNewline "  ${AMBER}→${NC} "
    $sw = Read-Host
    if ($sw -eq "y" -or $sw -eq "Y") {
        if ($RAM_GB -ge 8) {
            $BRAIN = "smart-fast-7b"; $BRAIN_LABEL = "Smart & Fast (7B)"
        } else {
            $BRAIN = "compact-3b"; $BRAIN_LABEL = "Compact (3B)"
        }
        Ok "Switched to $BRAIN_LABEL"
    }
}

Write-Host ""
Ok "Brain: $BRAIN_LABEL"
Write-Host ""
Start-Sleep -Milliseconds 500

# ============================================================================
# STEP 3: CHOOSE YOUR COMPANION
# ============================================================================

Write-Host "  ${BOLD}Choose your companion:${NC}"
Write-Host "  ${DIM}This shapes how your AI talks, thinks, and vibes with you.${NC}"
Write-Host ""
Write-Host "    ${AMBER}[1]${NC} 🐱  Cat       ${DIM}— chill, aloof, sarcastic${NC}"
Write-Host "    ${AMBER}[2]${NC} 🐶  Dog       ${DIM}— eager, enthusiastic, loyal${NC}"
Write-Host "    ${AMBER}[3]${NC} 🐧  Penguin   ${DIM}— precise, formal, organized${NC}"
Write-Host "    ${AMBER}[4]${NC} 🦊  Fox       ${DIM}— curious, clever, playful${NC}"
Write-Host "    ${AMBER}[5]${NC} 🦉  Owl       ${DIM}— wise, analytical, patient${NC}"
Write-Host "    ${AMBER}[6]${NC} 🐉  Dragon    ${DIM}— bold, dramatic, powerful${NC}"
Write-Host ""

$PET_CHOICE = Ask-Choice -Min 1 -Max 6 -Default 4

switch ($PET_CHOICE) {
    1 { $PET = "cat";     $PET_EMOJI = "🐱"; $PET_NAME = "Whiskers"
        $PET_ART = @"
         /\_/\
        ( o.o )
         > ^ <
        /|   |\
       (_|   |_)
"@ }
    2 { $PET = "dog";     $PET_EMOJI = "🐶"; $PET_NAME = "Buddy"
        $PET_ART = @"
         / \__
        (    @\___
         /         O
        /   (_____/
       /_____/   U
"@ }
    5 { $PET = "owl";     $PET_EMOJI = "🦉"; $PET_NAME = "Sage"
        $PET_ART = @"
         ,___,
         (O,O)
         /)  )
        /""-""
"@ }
    6 { $PET = "dragon";  $PET_EMOJI = "🐉"; $PET_NAME = "Cinder"
        $PET_ART = @"
            __====-_  _-====___
      _--^^^  //    \/    \\  ^^^--_
          __  ||    ||    ||  __
         '  '^^^^  ^^  ^^^^'  '
"@ }
    4 { $PET = "fox";     $PET_EMOJI = "🦊"; $PET_NAME = "Ember"
        $PET_ART = @"
         /\   /\
        /  \_/  \
       |  o   o  |
        \  .___.  /
         \______/
"@ }
    default { $PET = "penguin"; $PET_EMOJI = "🐧"; $PET_NAME = "Sir Wadsworth"
        $PET_ART = @"
            .___.
           /     \
          | O _ O |
          /  \_/  \
         / |     | \
        /__|     |__\
           |_____|
            _/ \_
"@ }
}

Write-Host ""
Ok "Companion: $PET_EMOJI $PET_NAME the $($PET.Substring(0,1).ToUpper() + $PET.Substring(1))"
Write-Host ""
Start-Sleep -Milliseconds 500

# ============================================================================
# STEP 4: WHO'S RUNNING THE SHOW AT HOME?
# ============================================================================

Write-Host ""
Write-Host "  ${BOLD}Now, who's running the show at home?${NC}"
Write-Host ""
Write-Host "  ${DIM}Every companion has someone at the fireside.${NC}"
Write-Host "  ${DIM}This is the mind behind ${PET_NAME} — your AI.${NC}"
Write-Host ""
Write-Host "  ${BOLD}Give your AI a name:${NC}"
Write-Host "  ${DIM}(default: Atlas)${NC}"
Write-Host ""
Write-Host -NoNewline "  ${AMBER}→${NC} "
$AGENT_NAME = Read-Host

if ([string]::IsNullOrWhiteSpace($AGENT_NAME)) { $AGENT_NAME = "Atlas" }
$AGENT_NAME = $AGENT_NAME.Substring(0,1).ToUpper() + $AGENT_NAME.Substring(1)

Write-Host ""
Write-Host "  ${BOLD}What's ${AGENT_NAME}'s style?${NC}"
Write-Host ""
Write-Host "    ${AMBER}[1]${NC} 🎯  Analytical  ${DIM}— data-driven, precise, sees the patterns${NC}"
Write-Host "    ${AMBER}[2]${NC} 🎨  Creative    ${DIM}— imaginative, lateral thinker${NC}"
Write-Host "    ${AMBER}[3]${NC} ⚡  Direct      ${DIM}— no-nonsense, efficient${NC}"
Write-Host "    ${AMBER}[4]${NC} 🌿  Warm        ${DIM}— empathetic, supportive${NC}"
Write-Host ""

$STYLE_CHOICE = Ask-Choice -Min 1 -Max 4 -Default 1

switch ($STYLE_CHOICE) {
    1       { $AGENT_STYLE = "analytical"; $STYLE_EMOJI = "🎯" }
    2       { $AGENT_STYLE = "creative";   $STYLE_EMOJI = "🎨" }
    3       { $AGENT_STYLE = "direct";     $STYLE_EMOJI = "⚡" }
    4       { $AGENT_STYLE = "warm";       $STYLE_EMOJI = "🌿" }
    default { $AGENT_STYLE = "analytical"; $STYLE_EMOJI = "🎯" }
}

$STYLE_LABEL = $AGENT_STYLE.Substring(0,1).ToUpper() + $AGENT_STYLE.Substring(1)

Write-Host ""
Ok "AI: $AGENT_NAME ($STYLE_EMOJI $STYLE_LABEL)"
Write-Host ""
Start-Sleep -Milliseconds 500

# ============================================================================
# STEP 5: CONFIRMATION CARD
# ============================================================================

Write-Host ""
Write-Host "       ${AMBER}${BOLD}◆  Ready to install${NC}"
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "          ${DIM}Owner${NC}         ${BOLD}${USER_NAME}${NC}"
Write-Host "          ${DIM}AI${NC}            ${BOLD}${AGENT_NAME} (${STYLE_EMOJI})${NC}"
Write-Host "          ${DIM}Companion${NC}     ${BOLD}${PET_EMOJI} ${PET_NAME}${NC}"
Write-Host "          ${DIM}Brain${NC}         ${BOLD}${BRAIN_LABEL}${NC}"
Write-Host "          ${DIM}Location${NC}      ${BOLD}~\.fireside${NC}"
Write-Host ""
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "       ${DIM}Press Enter to start, or Ctrl+C to cancel.${NC}"
Read-Host | Out-Null
Write-Host ""

# ============================================================================
# STEP 6: INSTALL
# ============================================================================

Write-Host "  ${BOLD}Setting things up...${NC}"
Write-Host ""

# ─── Python ───
$PYTHON = $null
foreach ($py in @("python3", "python", "py")) {
    $cmd = Get-Command $py -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $ver = & $cmd.Source --version 2>&1
            if ($ver -match "(\d+)\.(\d+)") {
                if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 10) {
                    $PYTHON = $cmd.Source
                    break
                }
            }
        } catch {}
    }
}

if (-not $PYTHON) {
    Info "Installing Python (one-time setup)..."
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if ($wg) {
        & winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent 2>$null
        $PYTHON = "python"
    } else {
        Fail "Please install Python 3.10+ from python.org and re-run."
    }
}
Ok "Python ready"

# ─── Node.js ───
$NODE_OK = $false
try {
    $nv = (& node --version) -replace 'v',''
    if ([int]($nv.Split('.')[0]) -ge 18) { $NODE_OK = $true }
} catch {}

if (-not $NODE_OK) {
    Info "Installing Node.js (one-time setup)..."
    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if ($wg) {
        & winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements --silent 2>$null
    } else {
        Fail "Please install Node.js 18+ from nodejs.org and re-run."
    }
}
Ok "Dashboard engine ready"

# ─── Clone/Update ───
if (Test-Path $FIRESIDE_DIR) {
    Info "Updating Fireside..."
    Push-Location $FIRESIDE_DIR
    & git pull --ff-only -q 2>$null
    Pop-Location
} else {
    Info "Downloading Fireside..."
    & git clone -q $REPO_URL $FIRESIDE_DIR
}
Ok "Source code ready"

Push-Location $FIRESIDE_DIR

# ─── Backend packages ───
Progress-Bar "Installing backend packages" 3
& $PYTHON -m pip install --upgrade pip -q 2>$null
& $PYTHON -m pip install -r requirements.txt -q 2>$null

# ─── Dashboard packages ───
Progress-Bar "Installing dashboard" 3
Push-Location dashboard
& npm install --silent 2>$null
Pop-Location

Write-Host ""

# ============================================================================
# GENERATE CONFIG + COMPANION STATE
# ============================================================================

$NOW = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

@"
node:
  name: ${USER_NAME}'s-fireside
  role: orchestrator

models:
  providers: {}
  aliases:
    default: local/${BRAIN}

plugins:
  enabled:
    - model-switch
    - watchdog
    - event-bus
    - working-memory
    - pipeline
    - consumer-api
    - brain-installer
    - companion
    - browse
    - personality

agent:
  name: "${AGENT_NAME}"
  style: "${AGENT_STYLE}"

companion:
  species: ${PET}
  name: "${PET_NAME}"
  owner: "${USER_NAME}"

pipeline:
  git_branching: false
"@ | Out-File -FilePath (Join-Path $FIRESIDE_DIR "valhalla.yaml") -Encoding UTF8

New-Item -ItemType Directory -Path $VALHALLA_DIR -Force | Out-Null

@"
{
  "species": "${PET}",
  "name": "${PET_NAME}",
  "owner": "${USER_NAME}",
  "agent": {
    "name": "${AGENT_NAME}",
    "style": "${AGENT_STYLE}"
  },
  "happiness": 80,
  "xp": 0,
  "level": 1,
  "streak": 0,
  "brain": "${BRAIN}",
  "version": "${VERSION}",
  "born": "${NOW}"
}
"@ | Out-File -FilePath (Join-Path $VALHALLA_DIR "companion_state.json") -Encoding UTF8

New-Item -ItemType Directory -Path $FIRESIDE_DIR -Force | Out-Null

@"
{
  "onboarded": true,
  "user_name": "${USER_NAME}",
  "personality": "friendly",
  "brain": "${BRAIN}",
  "agent": {
    "name": "${AGENT_NAME}",
    "style": "${AGENT_STYLE}"
  },
  "companion": {
    "species": "${PET}",
    "name": "${PET_NAME}"
  },
  "installed_at": "${NOW}"
}
"@ | Out-File -FilePath (Join-Path $FIRESIDE_DIR "onboarding.json") -Encoding UTF8

Ok "Configuration saved"
Write-Host ""

# ============================================================================
# START FIRESIDE
# ============================================================================

Write-Host "  ${BOLD}Starting Fireside...${NC}"
Write-Host ""

$bifrostJob = Start-Job -ScriptBlock {
    Set-Location $using:FIRESIDE_DIR
    & $using:PYTHON bifrost.py 2>&1 | Out-Null
}

$dashJob = Start-Job -ScriptBlock {
    Set-Location (Join-Path $using:FIRESIDE_DIR "dashboard")
    & npm run dev 2>&1 | Out-Null
}

Progress-Bar "$AGENT_NAME and $PET_NAME are getting ready" 5

# ============================================================================
# 🔥 SUCCESS
# ============================================================================

Write-Host ""
Write-Host ""
Write-Host "       ${AMBER}${BOLD}◆  F I R E S I D E   I S   L I V E  ◆${NC}"
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "       $AGENT_NAME is at the fireside.   $PET_NAME is by their side."
Write-Host "       ${AMBER}🔥${NC}                          $PET_EMOJI"
Write-Host ""
Write-Host "${AMBER}${PET_ART}${NC}"
Write-Host ""
Write-Host "       ${BOLD}${AGENT_NAME}${NC} ${DIM}&${NC} ${BOLD}${PET_EMOJI} ${PET_NAME}${NC} ${DIM}are ready for you,${NC} ${BOLD}${USER_NAME}${NC}${DIM}.${NC}"
Write-Host ""
Write-Host "       ${BOLD}Dashboard${NC}   →  ${AMBER}http://localhost:3000${NC}"
Write-Host "       ${BOLD}Backend${NC}     →  ${DIM}http://localhost:8765${NC}"
Write-Host ""
Write-Host ""
Write-Host "       ${AMBER}${BOLD}◆  Things to try${NC}"
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "          ${AMBER}1.${NC}  Say ${ITALIC}`"Hello ${PET_NAME}!`"${NC}"
Write-Host "          ${AMBER}2.${NC}  Ask ${ITALIC}`"Take me for a walk`"${NC}"
Write-Host "          ${AMBER}3.${NC}  Say ${ITALIC}`"Remember: I like coffee black`"${NC}"
Write-Host "          ${AMBER}4.${NC}  Ask ${ITALIC}`"Translate 'hello' to Japanese`"${NC}"
Write-Host ""
Write-Host "       ${DIM}─────────────────────────────────────────────${NC}"
Write-Host ""
Write-Host "       ${ITALIC}${DIM}`"Day 1, it follows instructions.${NC}"
Write-Host "       ${ITALIC}${DIM} Day 90, it has instinct.`"${NC}"
Write-Host ""

# Open browser
Start-Process "http://localhost:3000"

Write-Host "  ${DIM}Fireside v${VERSION} · Press Ctrl+C to stop${NC}"
Write-Host ""

# Keep alive
try {
    while ($true) {
        Start-Sleep -Seconds 5
        if ($bifrostJob.State -eq "Failed") { Warn "Backend stopped unexpectedly" }
        if ($dashJob.State -eq "Failed") { Warn "Dashboard stopped unexpectedly" }
    }
} finally {
    Write-Host ""
    Write-Host "  ${AMBER}🔥${NC} ${DIM}Fireside stopped. See you next time.${NC}"
    Write-Host ""
    Stop-Job $bifrostJob, $dashJob -ErrorAction SilentlyContinue
    Remove-Job $bifrostJob, $dashJob -ErrorAction SilentlyContinue
    Pop-Location
}
