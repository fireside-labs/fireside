#!/bin/bash
# Valhalla Sprint Pipeline — Quick Status Check
# Usage: bash sprints/current/gates/check_status.sh

GATES_DIR="$(cd "$(dirname "$0")" && pwd)"
SPRINT_FILE="$(dirname "$GATES_DIR")/SPRINT.md"

echo "=== Valhalla Sprint Pipeline ==="
echo ""

if [ -f "$SPRINT_FILE" ]; then
  head -1 "$SPRINT_FILE"
else
  echo "No active sprint found. Ask Odin to run /sprint."
  exit 0
fi

echo "---"
echo ""

# Phase 1: Build
THOR="⬜ working"; FREYA="⬜ working"
[ -f "$GATES_DIR/gate_thor.md" ] && THOR="✅ done"
[ -f "$GATES_DIR/gate_freya.md" ] && FREYA="✅ done"
echo "  Phase 1 — Build:"
echo "    Thor:  $THOR"
echo "    Freya: $FREYA"

if [ -f "$GATES_DIR/gate_thor.md" ] && [ -f "$GATES_DIR/gate_freya.md" ]; then
  echo "  ✅ Build phase COMPLETE"
else
  echo "  ⬜ Build phase IN PROGRESS"
fi
echo ""

# Phase 2: Security Audit
HEIMDALL="⬜ pending"
[ -f "$GATES_DIR/audit_heimdall.md" ] && HEIMDALL="📝 audit written"
[ -f "$GATES_DIR/gate_heimdall.md" ] && HEIMDALL="✅ audit passed"
echo "  Phase 2 — Security Audit:"
echo "    Heimdall: $HEIMDALL"
echo ""

# Phase 3: UX Review
VALKYRIE="⬜ pending"
[ -f "$GATES_DIR/review_valkyrie.md" ] && VALKYRIE="📝 review written"
[ -f "$GATES_DIR/gate_valkyrie.md" ] && VALKYRIE="✅ review complete"
echo "  Phase 3 — UX & Business Review:"
echo "    Valkyrie: $VALKYRIE"
echo ""

# Overall
if [ -f "$GATES_DIR/gate_valkyrie.md" ]; then
  echo "🚀 Sprint complete! Ready for Odin to archive and start next sprint."
else
  echo "⏳ Sprint in progress..."
fi
