#!/usr/bin/env bash
# ============================================================================
# 🔥 Fireside Installer
#
# Usage:
#   curl -fsSL getfireside.ai/install | bash
#
# What this does:
#   1. Check your system (macOS or Linux)
#   2. Make sure Python and Node.js are ready
#   3. Download Fireside
#   4. Set everything up
#   5. Start your AI companion
#   6. Open your browser — say hi to your pet!
#
# No technical knowledge required.
# ============================================================================

set -euo pipefail

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
AMBER='\033[38;5;214m'
DIM='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

FIRESIDE_DIR="$HOME/.fireside"
REPO_URL="https://github.com/JordanFableFur/valhalla-mesh.git"
TOTAL_STEPS=7
CURRENT_STEP=0

# ─── Helpers ───
step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    echo -e "${AMBER}[$CURRENT_STEP/$TOTAL_STEPS]${NC} ${BOLD}$1${NC}"
}
ok()    { echo -e "  ${GREEN}✔${NC} $1"; }
info()  { echo -e "  ${DIM}$1${NC}"; }
warn()  { echo -e "  ${AMBER}⚠${NC} $1"; }
fail()  { echo -e "\n  ${RED}✗ $1${NC}\n"; exit 1; }
check_cmd() { command -v "$1" &> /dev/null; }

# ─── Cleanup on exit ───
cleanup() {
    echo ""
    echo -e "${DIM}────────────────────────────────────────${NC}"
    echo -e "  ${AMBER}🔥${NC} Fireside stopped. See you next time."
    echo -e "${DIM}────────────────────────────────────────${NC}"
    echo ""
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

# ============================================================================
# 🔥 HEADER
# ============================================================================

echo ""
echo -e "${AMBER}${BOLD}"
echo "    ╔══════════════════════════════════════╗"
echo "    ║                                      ║"
echo "    ║     🔥  Fireside Installer  🔥       ║"
echo "    ║                                      ║"
echo "    ║   Your AI companion, one step away   ║"
echo "    ║                                      ║"
echo "    ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================================
# [1/7] Check your system
# ============================================================================

step "Checking your system..."

OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" == "Darwin" ]]; then
    os_name="macOS"
    if [[ "$ARCH" == "arm64" ]]; then
        hw_name="Apple Silicon"
    else
        hw_name="Intel"
    fi
elif [[ "$OS" == "Linux" ]]; then
    os_name="Linux"
    hw_name="$ARCH"
else
    fail "Sorry, Fireside currently supports macOS and Linux. Windows users: try WSL2."
fi

ok "$os_name ($hw_name)"

# Detect RAM
RAM_GB=0
if [[ "$OS" == "Darwin" ]]; then
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    RAM_GB=$((RAM_BYTES / 1073741824))
elif [[ -f /proc/meminfo ]]; then
    RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    RAM_GB=$((RAM_KB / 1048576))
fi
ok "${RAM_GB}GB RAM detected"

# GPU Info
GPU="none"
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    GPU="Apple Silicon (shared ${RAM_GB}GB)"
    ok "GPU: $GPU"
elif check_cmd nvidia-smi; then
    GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    ok "GPU: $GPU"
else
    info "No dedicated GPU detected — Fireside will use CPU (slower but works)"
fi

# Recommend model size
if [[ "$RAM_GB" -ge 32 ]]; then
    MODEL_REC="Deep Thinker (35B) — best quality"
elif [[ "$RAM_GB" -ge 16 ]]; then
    MODEL_REC="Smart & Fast (7B) — recommended for your hardware"
else
    MODEL_REC="Compact (3B) — optimized for your RAM"
fi
info "Recommended brain: $MODEL_REC"

# ============================================================================
# [2/7] Setting up Python
# ============================================================================

step "Setting up Python..."

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
    warn "Python 3.10+ not found — installing it for you..."
    if [[ "$OS" == "Darwin" ]]; then
        if ! check_cmd brew; then
            info "Installing Homebrew first (macOS package manager)..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.12
        PYTHON="python3.12"
    else
        sudo apt update -qq && sudo apt install -y -qq python3.12 python3.12-venv python3-pip
        PYTHON="python3.12"
    fi
fi
ok "Python ready ($($PYTHON --version 2>&1 | grep -oE 'Python [0-9.]+'))"

# ============================================================================
# [3/7] Setting up Node.js
# ============================================================================

step "Setting up the dashboard..."

NODE_OK=false
if check_cmd node; then
    NODE_VER=$(node --version | grep -oE '[0-9]+' | head -1)
    if [[ "$NODE_VER" -ge 18 ]]; then
        NODE_OK=true
    fi
fi

if [[ "$NODE_OK" == false ]]; then
    warn "Installing Node.js (needed for the dashboard)..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install node@20
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y -qq nodejs
    fi
fi
ok "Dashboard engine ready (Node $(node --version))"

# ============================================================================
# [4/7] Download Fireside
# ============================================================================

step "Downloading Fireside..."

if [[ -d "$FIRESIDE_DIR" ]]; then
    info "Fireside already installed — updating..."
    cd "$FIRESIDE_DIR"
    git pull --ff-only -q 2>/dev/null || true
else
    git clone -q "$REPO_URL" "$FIRESIDE_DIR"
    cd "$FIRESIDE_DIR"
fi
ok "Source code ready"

# ============================================================================
# [5/7] Installing packages
# ============================================================================

step "Installing packages (this may take a minute)..."

# Python dependencies
$PYTHON -m pip install --upgrade pip -q 2>/dev/null
$PYTHON -m pip install -r requirements.txt -q 2>/dev/null
ok "Backend packages installed"

# Dashboard dependencies
cd dashboard
npm install --silent 2>/dev/null
cd ..
ok "Dashboard packages installed"

# ============================================================================
# [6/7] Configuring Fireside
# ============================================================================

step "Configuring Fireside..."

if [[ ! -f "valhalla.yaml" ]]; then
    cat > valhalla.yaml << 'EOF'
node:
  name: my-fireside
  role: orchestrator

models:
  providers: {}
  aliases:
    default: local/default

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

pipeline:
  git_branching: false
EOF
    ok "Fresh config created"
else
    ok "Config already exists"
fi

# Create data directory
mkdir -p "$HOME/.valhalla"
ok "Data directory ready"

# ============================================================================
# [7/7] Starting Fireside!
# ============================================================================

step "Starting Fireside!"

# Start backend
$PYTHON bifrost.py &
BIFROST_PID=$!
info "Backend starting..."

# Start dashboard
cd dashboard
npm run dev &> /dev/null &
DASH_PID=$!
cd ..
info "Dashboard starting..."

# Wait for services to be ready
echo ""
info "Warming up..."
sleep 4

# ============================================================================
# 🔥 SUCCESS!
# ============================================================================

echo ""
echo -e "${GREEN}${BOLD}"
echo "    ╔══════════════════════════════════════╗"
echo "    ║                                      ║"
echo "    ║        🔥 Fireside is running!       ║"
echo "    ║                                      ║"
echo "    ╚══════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  ${BOLD}Dashboard${NC}   →  ${AMBER}http://localhost:3000${NC}"
echo -e "  ${BOLD}Backend${NC}     →  ${DIM}http://localhost:8765${NC}"
echo ""
echo -e "  ${DIM}────────────────────────────────────────${NC}"
echo ""
echo -e "  🐧 ${BOLD}Your companion is waiting.${NC}"
echo -e "     Open the link above and say hello!"
echo ""
echo -e "  ${DIM}────────────────────────────────────────${NC}"
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
