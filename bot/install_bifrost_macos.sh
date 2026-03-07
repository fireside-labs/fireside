#!/bin/bash
# install_bifrost_macos.sh
# Run once on Odin (macOS) to install Bifrost as a launchd service.
# It will auto-start on login and restart if it crashes.

set -e

PYTHON=$(which python3)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="ai.bifrost.bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_DIR="$HOME/.openclaw/logs"

mkdir -p "$LOG_DIR"

echo "Installing Bifrost..."
echo "  Python:  $PYTHON"
echo "  Script:  $SCRIPT_DIR/bifrost.py"
echo "  Plist:   $PLIST_PATH"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${SCRIPT_DIR}/bifrost.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/bifrost.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/bifrost.err</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Unload old version if present
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load and start
launchctl load "$PLIST_PATH"

echo ""
echo "Bifrost installed as launchd service '$PLIST_LABEL'."
echo "Logs: $LOG_DIR/bifrost.log"
echo ""
echo "Useful commands:"
echo "  launchctl stop  $PLIST_LABEL"
echo "  launchctl start $PLIST_LABEL"
echo "  tail -f $LOG_DIR/bifrost.log"
