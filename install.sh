#!/usr/bin/env bash
# ============================================================================
# Valhalla Mesh V2 — One-Line Installer
#
# Usage:
#   curl -fsSL https://get.valhalla.ai | bash
#
# What it does:
#   1. Detect OS (macOS/Linux)
#   2. Install Python 3.10+ if needed
#   3. Install Node.js 18+ if needed
#   4. Clone valhalla-mesh-v2 repo
#   5. Install Python + Node dependencies
#   6. Generate default valhalla.yaml
#   7. Start Bifrost + dashboard
#   8. Open browser → onboarding wizard
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

VALHALLA_DIR="$HOME/valhalla-mesh-v2"
REPO_URL="https://github.com/openclaw/valhalla-mesh-v2.git"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { echo -e "${BLUE}ℹ${NC}  $1"; }
ok()    { echo -e "${GREEN}✅${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $1"; }
fail()  { echo -e "${RED}❌${NC} $1"; exit 1; }

check_cmd() { command -v "$1" &> /dev/null; }

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

echo ""
echo -e "${BOLD}⚡ Valhalla Mesh V2 Installer${NC}"
echo -e "   ${BLUE}Your personal AI mesh, one click away.${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Detect OS
# ---------------------------------------------------------------------------

OS="$(uname -s)"
ARCH="$(uname -m)"
info "Detected: $OS ($ARCH)"

if [[ "$OS" != "Darwin" && "$OS" != "Linux" ]]; then
    fail "Unsupported OS: $OS. Valhalla supports macOS and Linux."
fi

# ---------------------------------------------------------------------------
# 2. Python 3.10+
# ---------------------------------------------------------------------------

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
    warn "Python 3.10+ not found. Installing..."
    if [[ "$OS" == "Darwin" ]]; then
        if ! check_cmd brew; then
            info "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.12
        PYTHON="python3.12"
    else
        sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip
        PYTHON="python3.12"
    fi
fi
ok "Python: $($PYTHON --version)"

# ---------------------------------------------------------------------------
# 3. Node.js 18+
# ---------------------------------------------------------------------------

if check_cmd node; then
    NODE_VER=$(node --version | grep -oE '[0-9]+' | head -1)
    if [[ "$NODE_VER" -lt 18 ]]; then
        warn "Node.js $NODE_VER found, need 18+. Upgrading..."
        if [[ "$OS" == "Darwin" ]]; then
            brew install node@20
        else
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt install -y nodejs
        fi
    fi
else
    warn "Node.js not found. Installing..."
    if [[ "$OS" == "Darwin" ]]; then
        brew install node@20
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
    fi
fi
ok "Node.js: $(node --version)"

# ---------------------------------------------------------------------------
# 4. Clone repo
# ---------------------------------------------------------------------------

if [[ -d "$VALHALLA_DIR" ]]; then
    info "Valhalla directory already exists at $VALHALLA_DIR"
    cd "$VALHALLA_DIR"
    git pull --ff-only 2>/dev/null || true
else
    info "Cloning Valhalla Mesh V2..."
    git clone "$REPO_URL" "$VALHALLA_DIR"
    cd "$VALHALLA_DIR"
fi
ok "Source code ready"

# ---------------------------------------------------------------------------
# 5. Install dependencies
# ---------------------------------------------------------------------------

info "Installing Python dependencies..."
$PYTHON -m pip install --upgrade pip -q
$PYTHON -m pip install -r requirements.txt -q
ok "Python dependencies installed"

info "Installing dashboard dependencies..."
cd dashboard
npm install --silent 2>/dev/null
cd ..
ok "Dashboard dependencies installed"

# ---------------------------------------------------------------------------
# 6. Generate default config (if not exists)
# ---------------------------------------------------------------------------

if [[ ! -f "valhalla.yaml" ]]; then
    info "Generating default config..."
    cat > valhalla.yaml << 'EOF'
node:
  name: my-device
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

pipeline:
  git_branching: false
EOF
    ok "Default config created"
else
    ok "Config exists"
fi

# ---------------------------------------------------------------------------
# 7. Detect hardware + recommend brain
# ---------------------------------------------------------------------------

echo ""
info "Detecting hardware..."
$PYTHON -c "
import platform, os, subprocess
cpu = platform.processor() or 'Unknown'
ram = 0
try:
    if platform.system() == 'Darwin':
        r = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
        ram = round(int(r.stdout.strip()) / (1024**3))
except: pass
print(f'   CPU: {cpu}')
print(f'   RAM: {ram} GB')
gpu = 'None detected'
try:
    if platform.system() == 'Darwin':
        r = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True)
        if 'Apple' in r.stdout:
            gpu = r.stdout.strip() + ' (unified memory)'
except: pass
print(f'   GPU: {gpu}')
"
echo ""

# ---------------------------------------------------------------------------
# 8. Start services
# ---------------------------------------------------------------------------

info "Starting Valhalla..."

# Start backend
echo -e "${BLUE}   Starting Bifrost (backend)...${NC}"
$PYTHON bifrost.py &
BIFROST_PID=$!

# Start dashboard
echo -e "${BLUE}   Starting Dashboard (frontend)...${NC}"
cd dashboard
npm run dev &
DASH_PID=$!
cd ..

sleep 3

# ---------------------------------------------------------------------------
# 9. Open browser
# ---------------------------------------------------------------------------

echo ""
echo -e "${GREEN}${BOLD}⚡ Valhalla is running!${NC}"
echo ""
echo -e "   Dashboard:  ${BOLD}http://localhost:3000${NC}"
echo -e "   Backend:    ${BOLD}http://localhost:8000${NC}"
echo ""
echo -e "   ${BLUE}Opening your browser now...${NC}"
echo ""

if [[ "$OS" == "Darwin" ]]; then
    open "http://localhost:3000"
else
    xdg-open "http://localhost:3000" 2>/dev/null || true
fi

echo -e "${YELLOW}Press Ctrl+C to stop Valhalla.${NC}"
wait
