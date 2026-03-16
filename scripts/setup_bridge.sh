#!/usr/bin/env bash
# ============================================================================
# 🌉 Fireside Anywhere Bridge — Tailscale Setup (macOS / Linux)
#
# Usage:  bash scripts/setup_bridge.sh
#
# This script:
#   1. Checks if Tailscale is already installed
#   2. Installs it if missing (brew on macOS, apt on Linux)
#   3. Authenticates with `tailscale up`
#   4. Displays the Tailscale IP for mobile app pairing
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
AMBER='\033[38;5;214m'
DIM='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
info() { echo -e "  ${DIM}$1${NC}"; }
warn() { echo -e "  ${AMBER}⚠${NC}  $1"; }
fail() { echo -e "\n  ${RED}✗ $1${NC}\n"; exit 1; }

echo ""
echo -e "  ${AMBER}${BOLD}◆  Fireside Anywhere Bridge Setup${NC}"
echo -e "  ${DIM}─────────────────────────────────────${NC}"
echo ""
echo -e "  ${DIM}This lets Ember (your phone) reach Atlas (your PC)${NC}"
echo -e "  ${DIM}from anywhere — no port forwarding needed.${NC}"
echo ""

# ── Step 1: Check for Tailscale ──
if command -v tailscale &> /dev/null; then
    ok "Tailscale is already installed"
else
    echo -e "  ${BOLD}Installing Tailscale...${NC}"
    echo ""

    OS="$(uname -s)"
    if [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew &> /dev/null; then
            fail "Homebrew is required. Install it from https://brew.sh"
        fi
        brew install --cask tailscale 2>/dev/null || brew install tailscale 2>/dev/null
    elif [[ "$OS" == "Linux" ]]; then
        curl -fsSL https://tailscale.com/install.sh | sh
    else
        fail "Unsupported OS: $OS"
    fi

    if ! command -v tailscale &> /dev/null; then
        fail "Tailscale installation failed. Install manually: https://tailscale.com/download"
    fi
    ok "Tailscale installed"
fi

# ── Step 2: Check if already connected ──
TS_STATUS=$(tailscale status --json 2>/dev/null || echo "{}")
if echo "$TS_STATUS" | grep -q '"BackendState":"Running"'; then
    ok "Tailscale is already connected"
else
    echo ""
    echo -e "  ${BOLD}Connecting to Tailscale...${NC}"
    echo -e "  ${DIM}A browser window will open for authentication.${NC}"
    echo ""

    # Support headless auth via environment variable
    if [[ -n "${TAILSCALE_AUTHKEY:-}" ]]; then
        info "Using authkey from TAILSCALE_AUTHKEY environment variable"
        tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="fireside-$(hostname -s)"
    else
        tailscale up --hostname="fireside-$(hostname -s)"
    fi

    ok "Tailscale connected"
fi

# ── Step 3: Display connection info ──
TS_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ifconfig | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' || echo "unknown")

echo ""
echo -e "  ${AMBER}${BOLD}◆  Anywhere Bridge is Active  ◆${NC}"
echo -e "  ${DIM}─────────────────────────────────────${NC}"
echo ""
echo -e "     ${DIM}Local IP${NC}       ${BOLD}${LOCAL_IP}${NC}"
echo -e "     ${DIM}Tailscale IP${NC}   ${BOLD}${TS_IP}${NC}"
echo ""
echo -e "  ${DIM}Your mobile app will auto-detect and connect.${NC}"
echo -e "  ${DIM}Make sure Tailscale is also installed on your phone.${NC}"
echo ""
echo -e "  ${DIM}iOS: https://apps.apple.com/app/tailscale/id1470499037${NC}"
echo -e "  ${DIM}Android: https://play.google.com/store/apps/details?id=com.tailscale.ipn${NC}"
echo ""
