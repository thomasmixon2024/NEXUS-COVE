#!/usr/bin/env bash
set -euo pipefail
MODEL="$1"

# `ollama list` talks to the daemon, which step 10 confirmed is up.
if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
  echo "✓ model $MODEL already present"
  exit 0
fi

echo "▶ Pulling $MODEL (one-time, ~400MB)"
ollama pull "$MODEL"
echo "✓ $MODEL ready"
