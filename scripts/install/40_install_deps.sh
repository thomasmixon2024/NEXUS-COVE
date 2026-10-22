#!/usr/bin/env bash
set -euo pipefail
VENV="$1"

echo "▶ Installing Python deps into $VENV"

# Try full dev install
if "$VENV/bin/pip" install -e ".[dev]" --quiet; then
  echo "✓ Deps installed (with dev extras)"
  exit 0
fi

# Fallback 1: wheels only
echo "⚠ Retrying with prebuilt wheels only…"
if "$VENV/bin/pip" install -e ".[dev]" --only-binary=:all: --quiet; then
  echo "✓ Deps installed (wheels only)"
  exit 0
fi

# Fallback 2: runtime only — no ruff/pytest on Python 3.14 + ARM64
echo "⚠ Dev extras unavailable on this Python — installing runtime only"
if "$VENV/bin/pip" install -e . --quiet; then
  echo "✓ Deps installed (runtime only — ruff/pytest skipped)"
  echo "   For linting: pipx install ruff   (or use Python 3.12)"
  exit 0
fi

echo "❌ Dependency install failed even at runtime-only."
echo "   Try: use Python 3.12 instead of 3.14"
exit 52
