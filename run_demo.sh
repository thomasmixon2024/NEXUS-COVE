#!/usr/bin/env bash
# run_demo.sh — orchestrates the install steps. Does no real work itself.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP_DIR="$ROOT/scripts/install"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
MODEL="${MODEL:-qwen2.5:0.5b}"
VENV="${VENV:-$ROOT/.venv}"

mkdir -p "$LOG_DIR"

# Parse flags (kept tiny on purpose — no TUI here)
SKIP_DEPS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-python-deps) SKIP_DEPS=1 ;;
    --model) shift; MODEL="$1" ;;
    --venv)  shift; VENV="$1" ;;
    -h|--help) echo "Usage: $0 [--model NAME] [--venv PATH] [--skip-python-deps]"; exit 0 ;;
  esac
  shift
done

# Each step is a separate script. Fail fast; the step prints the fix.
run_step() {
  local name="$1"; shift
  local log="$LOG_DIR/${name}-$(date +%Y%m%d-%H%M%S).log"
  echo "▶ $name"
  if ! bash "$STEP_DIR/$name.sh" "$@" 2>&1 | tee "$log"; then
    echo
    echo "❌ $name failed. Log: $log"
    echo "   → Fix what it printed above, then re-run: $0"
    exit 1
  fi
}

run_step 00_check_prereqs
run_step 10_ensure_ollama
run_step 20_ensure_venv     "$VENV"
run_step 30_ensure_model    "$MODEL"
[ "$SKIP_DEPS" = "1" ] || run_step 40_install_deps "$VENV"
run_step 90_verify          "$VENV" "$MODEL"

echo
echo "✅ All steps passed. Start the stack with: ./cove-testbed.sh --model --no-browser"
