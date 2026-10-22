#!/usr/bin/env bash
set -euo pipefail
VENV="$1"

echo "▶ Installing Python deps into $VENV"

# Try normal install first.
if "$VENV/bin/pip" install -e ".[dev]" --quiet; then
  echo "✓ Deps installed"
  exit 0
fi

# Fallback: wheels only. This is your most likely recovery path on 3.14+aarch64.
echo "⚠ Normal install failed — retrying with prebuilt wheels only"
if "$VENV/bin/pip" install -e ".[dev]" --only-binary=:all: --quiet; then
  echo "✓ Deps installed (wheels only)"
  exit 0
fi

echo "❌ Dependency install failed even with wheels."
echo "   Likely cause: a package needs to compile, but Python.h is missing."
echo "   Try: apt install python3.14-dev   (or pin Python to 3.12 in pyproject.toml)"
exit 52
