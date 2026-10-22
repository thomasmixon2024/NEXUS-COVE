#!/usr/bin/env bash
# ============================================================
# Nexus Cove - run every installer in order, stop on failure
# ============================================================
set -Eeuo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEPS=(
    01_install_chromium.sh
    02_setup_required_skills.sh
    03_setup_required_plugins.sh
    04_setup_optional_skills.sh
    05_setup_optional_plugins.sh
)

for step in "${STEPS[@]}"; do
    echo "--> ${step}"
    if ! bash "${DIR}/${step}"; then
        echo -e "\033[0;31m[FAILURE]\033[0m Stopped at ${step}. Fix it, then re-run run_all.sh."
        exit 1
    fi
done

echo -e "\033[0;32m[SUCCESS]\033[0m All installers finished."
echo -e "\033[0;35mRestart Claude Code so skills and plugins load.\033[0m"
echo -e "\033[1;35m  claude plugin list\033[0m"
