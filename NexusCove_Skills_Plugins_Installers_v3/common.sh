#!/usr/bin/env bash
# ============================================================
# Nexus Cove - shared helpers (sourced by every installer)
# Do not execute directly.
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BRIGHT_PURPLE='\033[1;35m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/Logs"
CLAUDE_HOME="${CLAUDE_HOME:-${HOME}/.claude}"
USER_SETTINGS="${CLAUDE_HOME}/settings.json"
NEXUS_COVE_ROOT="${NEXUS_COVE_ROOT:-${HOME}/NEXUS-COVE}"
LOG_FILE=""

success() { printf '%b[SUCCESS]%b %s\n' "$GREEN" "$NC" "$*"; }
failure() { printf '%b[FAILURE]%b %s\n' "$RED" "$NC" "$*"; }
warn()    { printf '%b[WARN]%b %s\n' "$YELLOW" "$NC" "$*"; }
info()    { printf '%b[INFO]%b %s\n' "$CYAN" "$NC" "$*"; }
suggest() { printf '%b%s%b\n' "$PURPLE" "$*" "$NC"; }
resolve() { printf '%b%s%b\n' "$BRIGHT_PURPLE" "$*" "$NC"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

init_log() {
    local name="$1"
    mkdir -p "$LOG_DIR"
    LOG_FILE="${LOG_DIR}/${name}_$(date +%Y%m%d_%H%M%S).log"
    exec > >(tee -a "$LOG_FILE") 2>&1
    trap 'failure "Unexpected error at line ${LINENO} (exit $?). Log: ${LOG_FILE}"' ERR
    echo "=============================================="
    echo " Nexus Cove: ${name}"
    echo " Started: $(date)"
    echo "=============================================="
}

finish_success() {
    echo
    success "=============================================="
    success " SUCCESS: $1"
    success " Log: ${LOG_FILE}"
    success "=============================================="
}

finish_failure() {
    echo
    failure "=============================================="
    failure " FAILURE: $1"
    failure " Log: ${LOG_FILE}"
    failure "=============================================="
    exit 1
}

require_python() {
    has_cmd python3 || { failure "python3 not found (needed to edit settings.json)"; return 1; }
}

require_claude() {
    if ! has_cmd claude; then
        failure "Claude Code CLI ('claude') not found on PATH"
        suggest "Install it with: npm install -g @anthropic-ai/claude-code"
        return 1
    fi
    info "Claude Code CLI: $(claude --version 2>/dev/null || echo 'version unknown')"
}

# Enables a plugin key in a Claude Code settings.json, creating the file if
# needed and keeping a timestamped backup of any existing file.
settings_enable_plugin() {
    local file="$1" key="$2"
    mkdir -p "$(dirname "$file")"
    if [[ -f "$file" ]]; then
        cp "$file" "${file}.bak.$(date +%Y%m%d_%H%M%S)"
    else
        echo '{}' > "$file"
    fi
    python3 - "$file" "$key" <<'PY'
import json
import sys

path, key = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
if not isinstance(data, dict):
    raise SystemExit(f"{path} does not contain a JSON object")
data.setdefault("enabledPlugins", {})[key] = True
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
    fh.write("\n")
PY
    success "Enabled ${key} in ${file}"
}

install_plugin() {
    local plugin="$1"
    if claude plugin install "$plugin"; then
        success "Claude Code installed plugin: ${plugin}"
    else
        warn "'claude plugin install' did not report success (it may already be installed). Enabling via settings."
    fi
    settings_enable_plugin "$USER_SETTINGS" "$plugin"
    if [[ -d "$NEXUS_COVE_ROOT" ]]; then
        settings_enable_plugin "${NEXUS_COVE_ROOT}/.claude/settings.json" "$plugin"
    else
        info "Project not found at ${NEXUS_COVE_ROOT}; skipping project settings (set NEXUS_COVE_ROOT to override)"
    fi
}

skill_present() {
    [[ -f "${CLAUDE_HOME}/skills/$1/SKILL.md" ]] || [[ -f "${NEXUS_COVE_ROOT}/.claude/skills/$1/SKILL.md" ]]
}

# Usage: write_skill <name> <<'EOF' ...SKILL.md content... EOF
# Never overwrites a skill that already exists at user or project level.
write_skill() {
    local name="$1" dir="${CLAUDE_HOME}/skills/$1"
    if skill_present "$name"; then
        cat > /dev/null
        info "Skill already present, left unchanged: ${name}"
        return 0
    fi
    mkdir -p "$dir"
    cat > "${dir}/SKILL.md"
    success "Installed skill: ${name} -> ${dir}/SKILL.md"
}
