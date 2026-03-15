#!/usr/bin/env bash
# ============================================================================
# 🔥 Fireside — Interactive Install Wizard
#
# Usage:
#   curl -fsSL getfireside.ai/install | bash
#
# The friendliest AI installer you've ever used.
# ============================================================================

set -euo pipefail

VERSION="1.0.0"

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
warn()  { echo -e "  ${AMBER}⚠${NC}  $1"; }
fail()  { echo -e "\n  ${RED}✗ $1${NC}\n"; exit 1; }
check_cmd() { command -v "$1" &> /dev/null; }

# Animated spinner
spinner() {
    local pid=$1
    local label="${2:-Working}"
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        echo -ne "\r  ${AMBER}${frames[$i]}${NC}  ${DIM}${label}${NC}  "
        i=$(( (i + 1) % 10 ))
        sleep 0.1
    done
    wait "$pid" 2>/dev/null
    echo -ne "\r  ${GREEN}✔${NC}  ${label}                    \n"
}

# Progress bar
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

# Ask with validation
ask_choice() {
    local prompt="$1"
    local min="$2"
    local max="$3"
    local default="$4"
    local choice=""

    while true; do
        echo -ne "  ${AMBER}→${NC} "
        read -r choice
        # Default on empty
        if [[ -z "$choice" ]]; then
            choice="$default"
            break
        fi
        # Validate numeric range
        if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge "$min" ]] && [[ "$choice" -le "$max" ]]; then
            break
        fi
        echo -e "  ${DIM}Hmm, that's not an option. Pick a number from ${min}-${max}.${NC}"
    done
    echo "$choice"
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
echo ""
echo -e "       ${AMBER}${BOLD}◆  W E L C O M E   T O   F I R E S I D E  ◆${NC}"
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "       ${AMBER}🔥${NC}  ${DIM}v${VERSION}${NC}"
echo ""
echo -e "       ${DIM}The AI companion that learns while you sleep.${NC}"
echo -e "       ${DIM}This takes about 2 minutes.${NC}"
echo ""
echo ""
sleep 1

# ============================================================================
# SYSTEM CHECK
# ============================================================================

echo -e "  ${BOLD}Checking your system...${NC}"
echo ""

OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" == "Darwin" ]]; then
    os_name="macOS"
    [[ "$ARCH" == "arm64" ]] && hw_name="Apple Silicon" || hw_name="Intel"
elif [[ "$OS" == "Linux" ]]; then
    os_name="Linux"
    hw_name="$ARCH"
else
    fail "Fireside supports macOS and Linux. Windows users: try WSL2."
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
GPU_VRAM=0
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    GPU_NAME="Apple Silicon (${RAM_GB}GB unified)"
    GPU_VRAM=$RAM_GB
elif check_cmd nvidia-smi; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
    GPU_VRAM=$((GPU_VRAM / 1024))
fi

ok "$os_name ($hw_name)"
ok "${RAM_GB}GB RAM"
ok "GPU: $GPU_NAME"
echo ""
sleep 0.5

# ============================================================================
# STEP 1: YOUR NAME
# ============================================================================

echo -e "  ${BOLD}What should your companion call you?${NC}"
echo -e "  ${DIM}(Just your first name is perfect)${NC}"
echo ""
echo -ne "  ${AMBER}→${NC} "
read -r USER_NAME

if [[ -z "$USER_NAME" ]]; then
    USER_NAME="friend"
fi
# Capitalize first letter
USER_NAME="$(echo "${USER_NAME:0:1}" | tr '[:lower:]' '[:upper:]')${USER_NAME:1}"

echo ""
echo -e "  ${DIM}Nice to meet you, ${NC}${BOLD}${USER_NAME}${NC}${DIM}. ☀️${NC}"
echo ""
sleep 0.8

# ============================================================================
# STEP 2: PICK A BRAIN
# ============================================================================

echo -e "  ${BOLD}Pick a brain for your AI:${NC}"
echo ""

# Smart recommendation based on RAM
if [[ "$RAM_GB" -ge 48 ]]; then
    REC="2"
elif [[ "$RAM_GB" -ge 16 ]]; then
    REC="1"
else
    REC="3"
fi

echo -e "    ${AMBER}[1]${NC} Smart & Fast   ${DIM}7B model · ~4GB download${NC}$( [[ "$REC" == "1" ]] && echo -e "  ${GREEN}← recommended for you${NC}" )"
echo -e "    ${AMBER}[2]${NC} Deep Thinker   ${DIM}35B model · ~20GB download${NC}$( [[ "$REC" == "2" ]] && echo -e "  ${GREEN}← recommended for you${NC}" )"
echo -e "    ${AMBER}[3]${NC} Compact        ${DIM}3B model · ~2GB download${NC}$( [[ "$REC" == "3" ]] && echo -e "  ${GREEN}← recommended for you${NC}" )"
echo ""

BRAIN_CHOICE=$(ask_choice "Pick 1-3" 1 3 "$REC")

case "$BRAIN_CHOICE" in
    2) BRAIN="deep-thinker-35b"; BRAIN_LABEL="Deep Thinker (35B)"; BRAIN_RAM=24 ;;
    3) BRAIN="compact-3b";       BRAIN_LABEL="Compact (3B)";       BRAIN_RAM=4 ;;
    *) BRAIN="smart-fast-7b";    BRAIN_LABEL="Smart & Fast (7B)";  BRAIN_RAM=8 ;;
esac

# RAM warning
if [[ "$RAM_GB" -lt "$BRAIN_RAM" ]]; then
    echo ""
    warn "The $BRAIN_LABEL brain works best with ${BRAIN_RAM}GB+ RAM."
    warn "You have ${RAM_GB}GB. It may run slowly."
    echo ""
    echo -e "  ${DIM}Switch to a smaller brain? (y/n)${NC}"
    echo -ne "  ${AMBER}→${NC} "
    read -r SWITCH
    if [[ "$SWITCH" == "y" || "$SWITCH" == "Y" ]]; then
        if [[ "$RAM_GB" -ge 8 ]]; then
            BRAIN="smart-fast-7b"; BRAIN_LABEL="Smart & Fast (7B)"
        else
            BRAIN="compact-3b"; BRAIN_LABEL="Compact (3B)"
        fi
        ok "Switched to $BRAIN_LABEL"
    fi
fi

echo ""
ok "Brain: $BRAIN_LABEL"
echo ""
sleep 0.5

# ============================================================================
# STEP 3: CHOOSE YOUR AI'S PERSONALITY
# ============================================================================

echo -e "  ${BOLD}Choose your AI's personality:${NC}"
echo -e "  ${DIM}This shapes how your AI talks, thinks, and vibes with you.${NC}"
echo ""
echo -e "    ${AMBER}[1]${NC} 🐱  Cat       ${DIM}— chill, aloof, sarcastic. gives advice like it's doing you a favor${NC}"
echo -e "    ${AMBER}[2]${NC} 🐶  Dog       ${DIM}— eager, enthusiastic, loyal. SO excited to help. BEST TASK EVER!!${NC}"
echo -e "    ${AMBER}[3]${NC} 🐧  Penguin   ${DIM}— precise, formal, organized. adjusts bowtie before every answer${NC}"
echo -e "    ${AMBER}[4]${NC} 🦊  Fox       ${DIM}— curious, clever, playful. investigates your question from every angle${NC}"
echo -e "    ${AMBER}[5]${NC} 🦉  Owl       ${DIM}— wise, analytical, patient. counted 47 ways to solve your problem${NC}"
echo -e "    ${AMBER}[6]${NC} 🐉  Dragon    ${DIM}— bold, dramatic, powerful. breathes fire at bad ideas${NC}"
echo ""

PET_CHOICE=$(ask_choice "Pick 1-6" 1 6 3)

case "$PET_CHOICE" in
    1) PET="cat";     PET_EMOJI="🐱"; PET_NAME="Whiskers"
       PET_ART='
        /\_/\
       ( o.o )
        > ^ <
       /|   |\
      (_|   |_)' ;;
    2) PET="dog";     PET_EMOJI="🐶"; PET_NAME="Buddy"
       PET_ART='
        / \__
       (    @\___
        /         O
       /   (_____/
      /_____/   U' ;;
    4) PET="fox";     PET_EMOJI="🦊"; PET_NAME="Ember"
       PET_ART='
        /\   /\
       /  \_/  \
      |  o   o  |
       \  .___.  /
        \______/' ;;
    5) PET="owl";     PET_EMOJI="🦉"; PET_NAME="Sage"
       PET_ART='
        ,___,
        (O,O)
        /)  )
       /""-""' ;;
    6) PET="dragon";  PET_EMOJI="🐉"; PET_NAME="Cinder"
       PET_ART='
           __====-_  _-====___
     _--^^^  //    \/    \\  ^^^--_
         __  ||    ||    ||  __
        ´  `^^^^  ^^  ^^^^´  `' ;;
    *) PET="penguin"; PET_EMOJI="🐧"; PET_NAME="Sir Wadsworth"
       PET_ART='
           .___.
          /     \
         | O _ O |
         /  \_/  \
        / |     | \
       /__|     |__\
          |_____|
           _/ \_' ;;
esac

echo ""
ok "Companion: $PET_EMOJI $PET_NAME the ${PET^}"
echo ""
sleep 0.5

# ============================================================================
# STEP 4: WHO'S RUNNING THE SHOW AT HOME?
# ============================================================================

echo ""
echo -e "  ${BOLD}Now, who's running the show at home?${NC}"
echo ""
echo -e "  ${DIM}Every companion has someone at the fireside.${NC}"
echo -e "  ${DIM}This is the mind behind ${PET_NAME} — your AI.${NC}"
echo ""
echo -e "  ${BOLD}Give your AI a name:${NC}"
echo -e "  ${DIM}(default: Atlas)${NC}"
echo ""
echo -ne "  ${AMBER}→${NC} "
read -r AGENT_NAME

if [[ -z "$AGENT_NAME" ]]; then
    AGENT_NAME="Atlas"
fi
# Capitalize first letter
AGENT_NAME="$(echo "${AGENT_NAME:0:1}" | tr '[:lower:]' '[:upper:]')${AGENT_NAME:1}"

echo ""
echo -e "  ${BOLD}What's ${AGENT_NAME}'s style?${NC}"
echo ""
echo -e "    ${AMBER}[1]${NC} 🎯  Analytical  ${DIM}— data-driven, precise, sees the patterns${NC}"
echo -e "    ${AMBER}[2]${NC} 🎨  Creative    ${DIM}— imaginative, lateral thinker, sees the possibilities${NC}"
echo -e "    ${AMBER}[3]${NC} ⚡  Direct      ${DIM}— no-nonsense, efficient, gets to the point${NC}"
echo -e "    ${AMBER}[4]${NC} 🌿  Warm        ${DIM}— empathetic, supportive, reads the room${NC}"
echo ""

AGENT_STYLE_CHOICE=$(ask_choice "Pick 1-4" 1 4 1)

case "$AGENT_STYLE_CHOICE" in
    1) AGENT_STYLE="analytical"; AGENT_STYLE_EMOJI="🎯" ;;
    2) AGENT_STYLE="creative";   AGENT_STYLE_EMOJI="🎨" ;;
    3) AGENT_STYLE="direct";     AGENT_STYLE_EMOJI="⚡" ;;
    4) AGENT_STYLE="warm";       AGENT_STYLE_EMOJI="🌿" ;;
    *) AGENT_STYLE="analytical"; AGENT_STYLE_EMOJI="🎯" ;;
esac

echo ""
ok "AI: ${AGENT_NAME} (${AGENT_STYLE_EMOJI} ${AGENT_STYLE^})"
echo ""
sleep 0.5

# ============================================================================
# STEP 5: CONFIRMATION CARD
# ============================================================================

echo ""
echo -e "       ${AMBER}${BOLD}◆  Ready to install${NC}"
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "          ${DIM}Owner${NC}         ${BOLD}${USER_NAME}${NC}"
echo -e "          ${DIM}AI${NC}            ${BOLD}${AGENT_NAME} (${AGENT_STYLE_EMOJI})${NC}"
echo -e "          ${DIM}Companion${NC}     ${BOLD}${PET_EMOJI} ${PET_NAME}${NC}"
echo -e "          ${DIM}Brain${NC}         ${BOLD}${BRAIN_LABEL}${NC}"
echo -e "          ${DIM}Location${NC}      ${BOLD}~/.fireside${NC}"
echo ""
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "       ${DIM}Press Enter to start, or Ctrl+C to cancel.${NC}"
read -r
echo ""

# ============================================================================
# INSTALL DEPENDENCIES
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
    info "Installing Python (one-time setup)..."
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
    info "Installing Node.js (one-time setup)..."
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

# ─── Backend packages ───
(
    $PYTHON -m pip install --upgrade pip -q 2>/dev/null
    $PYTHON -m pip install -r requirements.txt -q 2>/dev/null
) &
spinner $! "Installing backend packages"

# ─── Dashboard packages ───
(
    cd dashboard
    npm install --silent 2>/dev/null
) &
spinner $! "Installing dashboard"

echo ""

# ============================================================================
# GENERATE CONFIG + COMPANION STATE
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

agent:
  name: "${AGENT_NAME}"
  style: "${AGENT_STYLE}"

companion:
  species: ${PET}
  name: "${PET_NAME}"
  owner: "${USER_NAME}"

pipeline:
  git_branching: false
EOF

mkdir -p "$HOME/.valhalla"

cat > "$HOME/.valhalla/companion_state.json" << EOF
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
  "born": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

# Write onboarding flag so dashboard skips its own wizard
mkdir -p "$HOME/.fireside"
cat > "$HOME/.fireside/onboarding.json" << ONBOARD
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
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
ONBOARD

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

# Animated waiting
(sleep 5) &
spinner $! "${AGENT_NAME} and ${PET_NAME} are getting ready"

# ============================================================================
# 🔥 SUCCESS
# ============================================================================

echo ""
echo ""
echo -e "       ${AMBER}${BOLD}◆  F I R E S I D E   I S   L I V E  ◆${NC}"
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "       ${AGENT_NAME} is at the fireside.   ${PET_NAME} is by their side."
echo -e "       ${AMBER}🔥${NC}                          ${PET_EMOJI}"
echo ""

# ASCII pet
echo -e "${AMBER}${PET_ART}${NC}"
echo ""
echo -e "       ${BOLD}${AGENT_NAME}${NC} ${DIM}&${NC} ${BOLD}${PET_EMOJI} ${PET_NAME}${NC} ${DIM}are ready for you,${NC} ${BOLD}${USER_NAME}${NC}${DIM}.${NC}"
echo ""
echo -e "       ${BOLD}Dashboard${NC}   →  ${AMBER}http://localhost:3000${NC}"
echo -e "       ${BOLD}Backend${NC}     →  ${DIM}http://localhost:8765${NC}"
echo ""
echo ""
echo -e "       ${AMBER}${BOLD}◆  Things to try${NC}"
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "          ${AMBER}1.${NC}  Say ${ITALIC}\"Hello ${PET_NAME}!\"${NC}"
echo -e "          ${AMBER}2.${NC}  Ask ${ITALIC}\"Take me for a walk\"${NC}"
echo -e "          ${AMBER}3.${NC}  Say ${ITALIC}\"Remember: I like coffee black\"${NC}"
echo -e "          ${AMBER}4.${NC}  Ask ${ITALIC}\"Translate 'hello' to Japanese\"${NC}"
echo ""
echo -e "       ${DIM}─────────────────────────────────────────────${NC}"
echo ""
echo -e "       ${ITALIC}${DIM}\"Day 1, it follows instructions.${NC}"
echo -e "       ${ITALIC}${DIM} Day 90, it has instinct.\"${NC}"
echo ""

# Open browser
if [[ "$OS" == "Darwin" ]]; then
    open "http://localhost:3000"
else
    xdg-open "http://localhost:3000" 2>/dev/null || true
fi

echo -e "  ${DIM}Fireside v${VERSION} · Press Ctrl+C to stop${NC}"
echo ""
wait
