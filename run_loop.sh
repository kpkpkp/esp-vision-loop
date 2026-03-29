#!/bin/bash
# Run the autonomous vision loop, then hand off to Claude Code for analysis.
# Ollama and Claude Code cannot coexist — this script sequences them.
#
# Usage:
#   ./run_loop.sh "draw a red circle centered on screen"
#   ./run_loop.sh "draw a blue hexagon" --dry-run
#   ./run_loop.sh "draw a red circle" --skip-build

set -e
cd "$(dirname "$0")"

GOAL="${1:?Usage: ./run_loop.sh \"goal description\" [--dry-run] [--skip-build]}"
shift

# --- RAM check ---
AVAIL=$(free -m | awk '/Mem:/{print $7}')
echo "=== ESP Vision Loop ==="
echo "Goal: $GOAL"
echo "RAM available: ${AVAIL}MB"

if [ "$AVAIL" -lt 5500 ]; then
    echo ""
    echo "WARNING: Only ${AVAIL}MB available. Ollama needs ~5500MB."
    echo "Close background apps and try again."
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo ""

# --- Pre-flight: USB permission grant ---
# Request USB permission now so it doesn't timeout mid-iteration.
# termux-usb -r prompts once, then caches the grant until USB replug.
USB_DEV=$(termux-usb -l 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0] if d else '')" 2>/dev/null || true)
if [ -n "$USB_DEV" ]; then
    echo "USB device found: $USB_DEV"
    echo "Requesting USB permission (tap OK on the dialog)..."
    termux-usb -r "$USB_DEV" -e /bin/true 2>/dev/null || true
    echo "USB permission granted."
else
    echo "No USB device detected — flash steps will be skipped."
fi

echo ""

# --- Run the loop (Ollama active, Claude Code off) ---
python3 orchestrator.py --goal "$GOAL" "$@"
EXIT_CODE=$?

# --- Stop Ollama to free RAM for Claude Code ---
echo ""
echo "=== Stopping Ollama to free RAM ==="
pkill -f ollama 2>/dev/null || true
sleep 2

# --- Launch Claude Code to analyze results ---
echo "=== Launching Claude Code to check results ==="
echo ""
exec claude -n "vision-loop" "Read the latest logs in logs/ (especially the highest-numbered iteration_*.json). Report what happened: did codegen succeed? Did the build pass? What was the vision score? If something failed, diagnose why and suggest the fix."
