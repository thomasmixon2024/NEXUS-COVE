#!/usr/bin/env bash
# build-venv-termux.sh — rebuild .venv-termux from scratch.
# Called by ~/install-nexus.sh. Requires python3.13 on PATH
# (installed by uv: `uv python install 3.13` + symlink at ~/.local/bin/python3.13).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
REPO_ROOT="$(pwd)"
echo "Repo: $REPO_ROOT"

# 1. Find a compatible interpreter (3.11–3.13)
PY=""
for cand in "$HOME/.local/bin/python3.13" python3.13 python3.12 python3.11; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver=$("$cand" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
        case "$ver" in
            3.11|3.12|3.13) PY="$cand"; break ;;
        esac
    fi
done
[ -n "$PY" ] || {
    echo "ERROR: no Python 3.11-3.13 found." >&2
    echo "Install one: uv python install 3.13 && ln -sf \$(uv python find 3.13) ~/.local/bin/python3.13" >&2
    exit 1
}
echo "Using: $PY  ($("$PY" --version))"

# 2. Nuke old venv and recreate
rm -rf "$REPO_ROOT/.venv-termux"
"$PY" -m venv "$REPO_ROOT/.venv-termux"
VPY="$REPO_ROOT/.venv-termux/bin/python"

# 3. Upgrade pip
"$VPY" -m pip install --upgrade pip setuptools wheel

# 4. Editable install with dev extras
"$VPY" -m pip install -e "$REPO_ROOT[dev]"

# 5. Sanity checks
echo
echo "── installed entry points ──"
ls -1 "$REPO_ROOT/.venv-termux/bin/" | grep -E '^cove-' || true
echo
echo "── import smoke ──"
"$VPY" -c "import nexus_cove; print('nexus_cove OK')"

# 6. Run tests (don't fail the build if tests fail — they may need env setup)
echo
echo "── pytest ──"
"$VPY" -m pytest -q || echo "(tests reported failures — venv is still built)"

echo
echo "✓ .venv-termux ready at $REPO_ROOT/.venv-termux"
echo "  activate: source .venv-termux/bin/activate"
