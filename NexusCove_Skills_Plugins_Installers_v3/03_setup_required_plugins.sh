#!/usr/bin/env bash
# ============================================================
# Nexus Cove - REQUIRED plugin: superpowers
# Installs superpowers@claude-plugins-official via the Claude
# Code CLI, enables it in user settings and in the Nexus Cove
# project (if present), then verifies the result.
# ============================================================
set -Eeuo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
init_log required_plugins

PLUGIN="superpowers@claude-plugins-official"

require_python || finish_failure "python3 is required"
require_claude || finish_failure "Claude Code CLI is required"

info "Installing ${PLUGIN}"
install_plugin "$PLUGIN"

if grep -q "\"${PLUGIN}\"[[:space:]]*:[[:space:]]*true" "$USER_SETTINGS"; then
    success "Verified ${PLUGIN} is enabled in ${USER_SETTINGS}"
else
    finish_failure "${PLUGIN} is not enabled in ${USER_SETTINGS}"
fi

finish_success "REQUIRED plugins setup complete"
suggest "NEXT STEPS / SUGGESTED ACTIONS:"
suggest "  1. Restart Claude Code so the plugin loads"
suggest "  2. Inside Claude Code, run /plugin to confirm superpowers is listed"
suggest "  3. If the CLI install failed, run /plugin install ${PLUGIN} inside Claude Code"
suggest "  4. Continue with 04_setup_optional_skills.sh"
resolve "RESOLUTION:"
resolve "  claude plugin install ${PLUGIN}"
resolve "  grep -n superpowers \"${USER_SETTINGS}\""
