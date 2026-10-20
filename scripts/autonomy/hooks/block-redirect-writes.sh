#!/bin/bash
# PreToolUse hook — blocks shell-redirect writes to repo
# exit 0 = allow, exit 2 = block
set -uo pipefail

INPUT=$(cat)
CMD=$(printf "%s" "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")
[ -z "$CMD" ] && exit 0

# Exempt the sanctioned path
if printf "%s" "$CMD" | grep -q "atomic_write\\.sh"; then
  exit 0
fi

# Block redirect to absolute repo path
if printf "%s" "$CMD" | grep -qE ">>?[[:space:]]*/root/NEXUS-COVE/"; then
  printf "BLOCKED: shell redirect to repo file. Use scripts/autonomy/atomic_write.sh <target> <src> instead.\\n" >&2
  exit 2
fi

# Block redirect to relative repo file when cwd is repo
if printf "%s" "$INPUT" | grep -q '"cwd":[[:space:]]*"/root/NEXUS-COVE"'; then
  if printf "%s" "$CMD" | grep -qE ">>?[[:space:]]*\\.[a-zA-Z0-9_.-]+"; then
    printf "BLOCKED: shell redirect to repo file. Use scripts/autonomy/atomic_write.sh instead.\\n" >&2
    exit 2
  fi
fi

# Block tee to repo
if printf "%s" "$CMD" | grep -qE "tee[[:space:]]+.*(/root/NEXUS-COVE/|\\./)"; then
  printf "BLOCKED: tee to repo. Use scripts/autonomy/atomic_write.sh instead.\\n" >&2
  exit 2
fi

exit 0
