#!/usr/bin/env bash
set -euo pipefail

fail() { echo "❌ $1"; echo "   Fix: $2"; exit 50; }

# 1. Are we where we think we are?
command -v python3 >/dev/null || fail "python3 not found" "apt install python3"
command -v curl    >/dev/null || fail "curl not found"    "apt install curl"
command -v ollama  >/dev/null || fail "ollama not found" \
  "pkg install ollama   (in TERMUX, not Ubuntu). Then: ollama serve"

# 2. Python version sanity — 3.14 is too new for many wheels.
PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PYVER" in
  3.1[1-3]) echo "✓ Python $PYVER ok" ;;
  3.14)     echo "⚠ Python 3.14 is very new — some packages may not have wheels yet." ;;
  *)        fail "Python $PYVER not supported" "install Python 3.11–3.13" ;;
esac

# 3. Disk space (model is ~400MB, venv ~200MB)
FREE_MB=$(df -Pk "$HOME" | awk 'NR==2 {print int($4/1024)}')
[ "$FREE_MB" -ge 1500 ] || fail "Only ${FREE_MB}MB free" "free at least 1.5GB"

echo "✓ Prerequisites look good"
