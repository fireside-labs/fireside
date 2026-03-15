#!/usr/bin/env bash
# ============================================================================
# 🔥 Fireside — Interactive Install Wizard
#
# Usage:
#   curl -fsSL getfireside.ai/install | bash
#
# What this does:
#   1. Check your system
#   2. Ask your name
#   3. Let you pick a brain size
#   4. Let you choose a companion
#   5. Download & install everything
#   6. Start Fireside + open your browser
# ============================================================================

set -euo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
AMBER='\033[38;5;214m'
DIM='\033[0;90m'
BOLD='\033[1m'
ITALIC='\033[3m'
NC='\033[0m'

FIRESIDE_DIR="$HOME/.fireside"
REPO_URL="https://github.com/JordanFableFur/valhalla-mesh.git"

# ─── Helpers ───
ok()    { echo -e "  ${GREEN}✔${NC} $1"; }
info()  { echo -e "  ${DIM}$1${NC}"; }
warn()  { echo -e "  ${AMBER}⚠${NC} $1"; }
fail()  { echo -e "\n  ${RED}✗ $1${NC}\n"; exit 1; }
check_cmd() { command -v "$1" &> /dev/null; }

# Simple progress bar
progress_bar() {
    local label="$1"
    local duration="${2:-3}"
    local width=30
    echo -ne "  ${DIM}${label}${NC} "
    for ((i=0; i<=width; i++)); do
        echo -ne "${AMBER}█${NC}"
        sleep "$(echo "scale=3; $duration / $width" | bc 2>/dev/null || echo "0.1")"
    done
    echo -e " ${GREEN}✔${NC}"
}

# ─── Cleanup on exit ───
cleanup() {
    echo ""
    echo -e "  ${AMBER}🔥${NC} ${DIM}Fireside stopped. See you next time.${NC}"
    echo ""
    jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

# ============================================================================
# HEADER
# ============================================================================

clear
echo ""
echo -e "${AMBER}"
echo "         ╔═══════════════════════════════╗"
echo "         ║                               ║"
echo "         ║    🔥  Welcome to Fireside    ║"
echo "         ║                               ║"
echo "         ║   Your AI companion awaits.   ║"
echo "         ║                               ║"
echo "         ╚═══════════════════════════════╝"
echo -e "${NC}"
sleep 1

# ============================================================================
# SYSTEM CHECK (silent, fast)
# ============================================================================

echo -e "  ${DIM}Checking your system...${NC}"

OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" == "Darwin" ]]; then
    os_name="macOS"
    [[ "$ARCH" == "arm64" ]] && hw_name="Apple Silicon" || hw_name="Intel"
elif [[ "$OS" == "Linux" ]]; then
    os_name="Linux"
    hw_name="$ARCH"
else
    fail "Sorry, Fireside supports macOS and Linux. Windows users: try WSL2."
fi

# RAM
RAM_GB=0
if [[ "$OS" == "Darwin" ]]; then
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    RAM_GB=$((RAM_BYTES / 1073741824))
elif [[ -f /proc/meminfo ]]; then
    RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    RAM_GB=$((RAM_KB / 1048576))
fi

# GPU
GPU_NAME="CPU only"
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    GPU_NAME="Apple Silicon (${RAM_GB}GB shared)"
elif check_cmd nvidia-smi; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
fi

ok "$os_name ($hw_name) · ${RAM_GB}GB RAM · $GPU_NAME"
echo ""
sleep 0.5

# ============================================================================
# STEP 1: YOUR NAME
# ============================================================================

echo -e "  ${BOLD}What should your companion call you?${NC}"
echo ""
echo -ne "  ${AMBER}→${NC} "
read -r USER_NAME

if [[ -z "$USER_NAME" ]]; then
    USER_NAME="friend"
fi

echo ""
echo -e "  ${DIM}Nice to meet you, ${NC}${BOLD}$USER_NAME${NC}${DIM}.${NC}"
echo ""
sleep 0.8

# ============================================================================
# STEP 2: PICK A BRAIN
# ============================================================================

echo -e "  ${BOLD}Pick a brain for your AI:${NC}"
echo ""

# Recommend based on RAM
if [[ "$RAM_GB" -ge 32 ]]; then
    REC="2"
    REC_LABEL=" ← recommended"
elif [[ "$RAM_GB" -ge 16 ]]; then
    REC="1"
    REC_LABEL=" ← recommended"
else
    REC="1"
    REC_LABEL=" ← recommended"
fi

echo -e "  ${AMBER}[1]${NC} Smart & Fast ${DIM}(7B model · ~4GB download)${NC}$( [[ "$REC" == "1" ]] && echo -e " ${GREEN}${REC_LABEL}${NC}" )"
echo -e "  ${AMBER}[2]${NC} Deep Thinker ${DIM}(35B model · ~20GB download)${NC}$( [[ "$REC" == "2" ]] && echo -e " ${GREEN}${REC_LABEL}${NC}" )"
echo -e "  ${AMBER}[3]${NC} Compact      ${DIM}(3B model · ~2GB download · lower quality)${NC}"
echo ""
echo -ne "  ${AMBER}→${NC} "
read -r BRAIN_CHOICE

case "$BRAIN_CHOICE" in
    2) BRAIN="deep-thinker-35b"; BRAIN_LABEL="Deep Thinker (35B)" ;;
    3) BRAIN="compact-3b";       BRAIN_LABEL="Compact (3B)" ;;
    *) BRAIN="smart-fast-7b";    BRAIN_LABEL="Smart & Fast (7B)" ;;
esac

echo ""
ok "Brain selected: $BRAIN_LABEL"
echo ""
sleep 0.5

# ============================================================================
# STEP 3: CHOOSE A COMPANION
# ============================================================================

echo -e "  ${BOLD}Choose your companion:${NC}"
echo ""
echo -e "    ${AMBER}[1]${NC} 🐱  Cat       ${DIM}— finds sunny spots, knocks things over${NC}"
echo -e "    ${AMBER}[2]${NC} 🐶  Dog       ${DIM}— found a stick. THE stick. Best day ever!${NC}"
echo -e "    ${AMBER}[3]${NC} 🐧  Penguin   ${DIM}— waddles with purpose, adjusts bowtie${NC}"
echo -e "    ${AMBER}[4]${NC} 🦊  Fox       ${DIM}— investigates suspicious bushes${NC}"
echo -e "    ${AMBER}[5]${NC} 🦉  Owl       ${DIM}— counted every tree. 47. you're welcome${NC}"
echo -e "    ${AMBER}[6]${NC} 🐉  Dragon    ${DIM}— breathes fire at dandelions${NC}"
echo ""
echo -ne "  ${AMBER}→${NC} "
read -r PET_CHOICE

case "$PET_CHOICE" in
    1) PET="cat";     PET_EMOJI="🐱"; PET_NAME="Whiskers" ;;
    2) PET="dog";     PET_EMOJI="🐶"; PET_NAME="Buddy" ;;
    4) PET="fox";     PET_EMOJI="🦊"; PET_NAME="Ember" ;;
    5) PET="owl";     PET_EMOJI="🦉"; PET_NAME="Sage" ;;
    6) PET="dragon";  PET_EMOJI="🐉"; PET_NAME="Cinder" ;;
    *) PET="penguin"; PET_EMOJI="🐧"; PET_NAME="Sir Wadsworth" ;;
esac

echo ""
ok "Companion: $PET_EMOJI $PET_NAME the ${PET^}"
echo ""
sleep 0.8

# ============================================================================
# INSTALL DEPENDENCIES (quiet, with progress)
# ============================================================================

echo -e "  ${BOLD}Setting things up...${NC}"
echo ""

# ─── Python ───
PYTHON=""
for py in python3.12 python3.11 python3.10 python3; do
    if check_cmd "$py"; then
        PY_VER=$("$py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
            PYTHON="$py"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    info "Installing Python (one-time)..."
    if [[ "$OS" == "Darwin" ]]; then
        if ! check_cmd brew; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/null
        fi
        brew install python@3.12 -q
        PYTHON="python3.12"
    else
        sudo apt update -qq && sudo apt install -y -qq python3.12 python3.12-venv python3-pip
        PYTHON="python3.12"
    fi
fi
ok "Python ready"

# ─── Node.js ───
NODE_OK=false
if check_cmd node; then
    NODE_VER=$(node --version | grep -oE '[0-9]+' | head -1)
    [[ "$NODE_VER" -ge 18 ]] && NODE_OK=true
fi

if [[ "$NODE_OK" == false ]]; then
    info "Installing Node.js (one-time)..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install node@20 -q
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1
        sudo apt install -y -qq nodejs
    fi
fi
ok "Dashboard engine ready"

# ─── Clone/Update ───
if [[ -d "$FIRESIDE_DIR" ]]; then
    info "Updating Fireside..."
    cd "$FIRESIDE_DIR"
    git pull --ff-only -q 2>/dev/null || true
else
    info "Downloading Fireside..."
    git clone -q "$REPO_URL" "$FIRESIDE_DIR"
    cd "$FIRESIDE_DIR"
fi
ok "Source code ready"

# ─── Pip + npm ───
progress_bar "Installing backend packages..." 4
$PYTHON -m pip install --upgrade pip -q 2>/dev/null
$PYTHON -m pip install -r requirements.txt -q 2>/dev/null

progress_bar "Installing dashboard..." 5
cd dashboard
npm install --silent 2>/dev/null
cd ..

echo ""

# ============================================================================
# GENERATE CONFIG WITH USER'S CHOICES
# ============================================================================

cat > valhalla.yaml << EOF
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

companion:
  species: ${PET}
  name: "${PET_NAME}"
  owner: "${USER_NAME}"

pipeline:
  git_branching: false
EOF

# Create data directory
mkdir -p "$HOME/.valhalla"

# Save companion state with user's choice
cat > "$HOME/.valhalla/companion_state.json" << EOF
{
  "species": "${PET}",
  "name": "${PET_NAME}",
  "owner": "${USER_NAME}",
  "happiness": 80,
  "xp": 0,
  "level": 1,
  "streak": 0,
  "born": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

ok "Configuration saved"
echo ""

# ============================================================================
# START FIRESIDE
# ============================================================================

echo -e "  ${BOLD}Starting Fireside...${NC}"
echo ""

# Start backend
$PYTHON bifrost.py &> /dev/null &
BIFROST_PID=$!

# Start dashboard
cd dashboard
npm run dev &> /dev/null &
DASH_PID=$!
cd ..

# Wait with a friendly animation
echo -ne "  ${DIM}Warming up"
for i in 1 2 3 4 5; do
    sleep 1
    echo -ne "."
done
echo -e "${NC}"
echo ""

# ============================================================================
# 🔥 SUCCESS
# ============================================================================

echo -e "${AMBER}"
echo "    ╔═══════════════════════════════════════════════╗"
echo "    ║                                               ║"
echo "    ║          🔥 Fireside is running! 🔥           ║"
echo "    ║                                               ║"
echo "    ╚═══════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  ${BOLD}Dashboard${NC}   →  ${AMBER}http://localhost:3000${NC}"
echo -e "  ${BOLD}Backend${NC}     →  ${DIM}http://localhost:8765${NC}"
echo ""
echo -e "  ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "  ${PET_EMOJI}  ${BOLD}${PET_NAME}${NC} ${DIM}is ready and waiting for you,${NC} ${BOLD}${USER_NAME}${NC}${DIM}.${NC}"
echo -e "     ${DIM}Open the link above and say hello!${NC}"
echo ""
echo -e "  ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "  ${ITALIC}${DIM}\"Day 1, it follows instructions."
echo -e "   Day 90, it has instinct.\"${NC}"
echo ""

# Open browser
if [[ "$OS" == "Darwin" ]]; then
    open "http://localhost:3000"
else
    xdg-open "http://localhost:3000" 2>/dev/null || true
fi

echo -e "  ${DIM}Press Ctrl+C to stop Fireside.${NC}"
echo ""
wait
