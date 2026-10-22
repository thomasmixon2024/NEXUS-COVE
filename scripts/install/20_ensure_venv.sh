#!/usr/bin/env bash
set -euo pipefail
VENV="$1"

if [ -x "$VENV/bin/python" ]; then
  echo "✓ venv exists at $VENV"
else
  echo "▶ Creating venv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip --quiet
fi

"$VENV/bin/python" -c 'import sys; print(f"✓ venv python {sys.version.split()[0]}")'
