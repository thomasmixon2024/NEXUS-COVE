#!/usr/bin/env bash
set -euo pipefail

API="http://127.0.0.1:11434/api/version"

if curl -s -m 2 "$API" >/dev/null 2>&1; then
  echo "✓ Ollama is already running"
  exit 0
fi

# It's installed but not running. We can't start it from proot cleanly.
echo "❌ Ollama is installed but not running."
echo
echo "   Ollama runs in Termux (native), not in this Ubuntu shell."
echo "   Open a Termux session and run:"
echo
echo "       ollama serve"
echo
echo "   Leave it running, then come back and re-run this installer."
exit 51
