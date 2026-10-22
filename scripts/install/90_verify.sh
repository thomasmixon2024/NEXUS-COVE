#!/usr/bin/env bash
set -euo pipefail
VENV="$1"; MODEL="$2"

echo "▶ Smoke test: one round-trip to the model"

START=$(date +%s%N)
REPLY=$(curl -s -m 30 http://127.0.0.1:11434/api/generate \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"Say hi in one sentence.\",\"stream\":false}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["response"].strip())')
END=$(date +%s%N)

MS=$(( (END - START) / 1000000 ))
echo "✓ Model replied in ${MS}ms: \"${REPLY:0:80}\""
echo
echo "✅ NEXUS-COVE is ready."
