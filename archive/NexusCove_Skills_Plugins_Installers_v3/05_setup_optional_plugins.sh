#!/usr/bin/env bash
# ============================================================
# Nexus Cove - OPTIONAL plugins
# No optional plugins are defined yet. Add entries to the
# OPTIONAL_PLUGINS array below and this script installs them.
# ============================================================
set -Eeuo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
init_log optional_plugins

OPTIONAL_PLUGINS=()

if [[ ${#OPTIONAL_PLUGINS[@]} -eq 0 ]]; then
    info "No optional plugins are defined. Nothing to install."
else
    require_python || finish_failure "python3 is required"
    require_claude || finish_failure "Claude Code CLI is required"
    for plugin in "${OPTIONAL_PLUGINS[@]}"; do
        install_plugin "$plugin"
        grep -q "\"${plugin}\"[[:space:]]*:[[:space:]]*true" "$USER_SETTINGS" \
            || finish_failure "${plugin} is not enabled in ${USER_SETTINGS}"
    done
fi

finish_success "OPTIONAL plugins setup complete"
suggest "NEXT STEPS / SUGGESTED ACTIONS:"
suggest "  1. Add plugin IDs (name@marketplace) to OPTIONAL_PLUGINS to install them"
suggest "  2. Re-run this script, then restart Claude Code"
resolve "RESOLUTION:"
resolve "  nano \"${SCRIPT_DIR}/05_setup_optional_plugins.sh\""
