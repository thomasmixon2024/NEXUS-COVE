#!/usr/bin/env bash
# ============================================================
# Nexus Cove - Chromium installer
# Termux: pkg install chromium
# Debian/Ubuntu (incl. proot): apt-get install chromium
# Verifies a headless render, then records CHROME_BIN.
# ============================================================
set -Eeuo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
init_log chromium_install

CONFIG_DIR="${SCRIPT_DIR}/claude_chromium_config"
mkdir -p "$CONFIG_DIR"

find_chromium() {
    local candidate
    if [[ -n "${CHROME_BIN:-}" && -x "$CHROME_BIN" ]]; then
        echo "$CHROME_BIN"
        return 0
    fi
    for candidate in chromium chromium-browser google-chrome google-chrome-stable; do
        if has_cmd "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

install_chromium() {
    if [[ -n "${PREFIX:-}" ]] && has_cmd pkg; then
        info "Termux detected; installing with pkg"
        pkg update -y || warn "pkg update reported a problem; continuing"
        pkg install -y chromium
    elif has_cmd apt-get; then
        local sudo_cmd=""
        if [[ "$EUID" -ne 0 ]]; then
            has_cmd sudo || { failure "Not root and sudo is not available"; return 1; }
            sudo_cmd="sudo"
        fi
        info "Debian/Ubuntu detected; installing with apt-get"
        $sudo_cmd apt-get update
        if apt-cache show chromium >/dev/null 2>&1; then
            $sudo_cmd apt-get install -y chromium
        else
            $sudo_cmd apt-get install -y chromium-browser
        fi
    else
        failure "No supported package manager found (need pkg or apt-get)"
        return 1
    fi
}

warn_if_snap_wrapper() {
    local bin="$1" real
    real="$(readlink -f "$bin" 2>/dev/null || echo "$bin")"
    if head -c 4096 "$real" 2>/dev/null | grep -aqi 'snap'; then
        warn "${bin} looks like a snap wrapper. Snap builds often fail in containers and proot."
        suggest "  Fallback: use the Termux pkg build or a Debian chromium package in proot."
    fi
}

verify_chromium() {
    local bin="$1" version dom
    version="$("$bin" --version 2>/dev/null | head -n 1 || true)"
    info "Chromium version: ${version:-unknown}"
    dom="$(timeout 60 "$bin" --headless --no-sandbox --disable-gpu --dump-dom 'data:text/html,<p>nexus-cove-ok</p>' 2>/dev/null || true)"
    if grep -q 'nexus-cove-ok' <<<"$dom"; then
        success "Headless render test passed"
        return 0
    fi
    failure "Headless render test failed"
    return 1
}

CHROME_BIN_PATH="$(find_chromium || true)"
if [[ -n "$CHROME_BIN_PATH" ]]; then
    info "Chromium already installed at ${CHROME_BIN_PATH}"
else
    install_chromium || finish_failure "Chromium installation failed (see output above)"
    CHROME_BIN_PATH="$(find_chromium || true)"
    [[ -n "$CHROME_BIN_PATH" ]] || finish_failure "Chromium installed but no binary found on PATH"
fi

warn_if_snap_wrapper "$CHROME_BIN_PATH"
verify_chromium "$CHROME_BIN_PATH" || finish_failure "Chromium does not render headless"

printf 'CHROME_BIN=%s\n' "$CHROME_BIN_PATH" > "${CONFIG_DIR}/chromium.env"
success "Wrote ${CONFIG_DIR}/chromium.env"

for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
    [[ -f "$rc" ]] || continue
    if ! grep -q '# nexus-cove chromium' "$rc"; then
        printf '\n# nexus-cove chromium\nexport CHROME_BIN="%s"\n' "$CHROME_BIN_PATH" >> "$rc"
        success "Added CHROME_BIN export to ${rc}"
    fi
done

finish_success "Chromium setup complete"
suggest "NEXT STEPS / SUGGESTED ACTIONS:"
suggest "  1. Reload your shell so CHROME_BIN is set"
suggest "  2. Re-run the headless test manually"
suggest "  3. Continue with 02_setup_required_skills.sh"
resolve "RESOLUTION:"
resolve "  source \"${CONFIG_DIR}/chromium.env\" && \"\$CHROME_BIN\" --headless --no-sandbox --dump-dom about:blank"
