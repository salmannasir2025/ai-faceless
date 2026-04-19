#!/bin/bash
# CLI Launcher for The Ledger - Compatible with older Macs
# For 2012 MacBook Pro with OpenCore Legacy Patcher

cd "$(dirname "$0")"

# Use system Python 3.9 (works better with tkinter on older systems)
PYTHON_CMD="/usr/bin/python3"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    🎬  THE LEDGER                               ║"
echo "║           CLI Mode - Optimized for Legacy Macs                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! $PYTHON_CMD --version >/dev/null 2>&1; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Python: $($PYTHON_CMD --version)"
echo ""

# Default topic or use argument
TOPIC="${1:-Financial Crime News}"

echo "🎬 Starting documentary creation..."
echo "   Topic: $TOPIC"
echo "   Mode: Dry-run (no API keys required)"
echo ""
echo "💡 Tip: To use your own topic, run: ./run_cli.command 'Your Topic Here'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the CLI
$PYTHON_CMD main.py "$TOPIC" --dry-run --style documentary

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Pipeline complete!"
echo "📁 Check output/videos/ for generated content"
echo ""
read -p "Press Enter to exit..."
