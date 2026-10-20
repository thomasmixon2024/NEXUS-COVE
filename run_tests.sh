#!/bin/bash
# ============================================================
# run_tests.sh — NEXUS-COVE test summary
# Version: 1.0.0  |  Generated: 2026-10-13
# ============================================================

# Colors
GREEN=$'\033[92m'
RED=$'\033[91m'
YELLOW=$'\033[93m'
PURPLE=$'\033[95m'
MAGENTA=$'\033[35m'
CYAN=$'\033[96m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

LOG_DIR="$HOME/NEXUS-COVE/Logs"
mkdir -p "$LOG_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG_FILE="$LOG_DIR/run_${TS}.log"

echo "${CYAN}${BOLD}=== NEXUS-COVE Test Run — ${TS} ===${RESET}"
echo "${CYAN}Log: $LOG_FILE${RESET}"
echo

declare -a NAMES=()
declare -a CODES=()

run_step() {
    local name="$1"; shift
    echo "${CYAN}▶ $name${RESET}"
    echo "--- $name ---" >> "$LOG_FILE"
    "$@" >> "$LOG_FILE" 2>&1
    local rc=$?
    NAMES+=("$name")
    CODES+=("$rc")
    if [ $rc -eq 0 ]; then
        echo "  ${GREEN}✓ PASS (exit 0)${RESET}"
    else
        echo "  ${RED}✗ FAIL (exit $rc)${RESET}"
    fi
    echo
}

# Step 1: Python version
run_step "Python version" .venv-termux/bin/python --version

# Step 2: Editable install check
run_step "Package installed" .venv-termux/bin/python -c "import nexus_cove; print(nexus_cove.__file__)"

# Step 3: Ruff lint
run_step "Ruff lint" .venv-termux/bin/python -m ruff check .

# Step 4: Compile check
run_step "Compileall" .venv-termux/bin/python -m compileall -q src tests

# Step 5: Test suite
run_step "Pytest suite" .venv-termux/bin/python -m pytest tests -q

# ---- Summary ----
echo "${BOLD}${CYAN}=== SUMMARY ===${RESET}"
TOTAL=${#NAMES[@]}
PASS=0
FAIL=0
for i in "${!NAMES[@]}"; do
    if [ "${CODES[$i]}" -eq 0 ]; then
        echo "  ${GREEN}✓ ${NAMES[$i]}${RESET}"
        PASS=$((PASS+1))
    else
        echo "  ${RED}✗ ${NAMES[$i]} (exit ${CODES[$i]})${RESET}"
        FAIL=$((FAIL+1))
    fi
done
echo
if [ $FAIL -eq 0 ]; then
    echo "${GREEN}${BOLD}STATUS: SUCCESS — $PASS/$TOTAL steps passed${RESET}"
    EXIT=0
elif [ $PASS -gt 0 ]; then
    echo "${YELLOW}${BOLD}STATUS: PARTIAL — $PASS passed, $FAIL failed${RESET}"
    EXIT=1
else
    echo "${RED}${BOLD}STATUS: FAILURE — $PASS/$TOTAL steps passed${RESET}"
    EXIT=1
fi
echo "${CYAN}Full log: $LOG_FILE${RESET}"
echo
echo "${PURPLE}Next Steps:${RESET}"
echo "${PURPLE}  1. Review failures above${RESET}"
echo "${PURPLE}  2. Inspect full log for tracebacks${RESET}"
echo
echo "${MAGENTA}Resolution commands:${RESET}"
echo "${MAGENTA}  re-run      : bash ~/NEXUS-COVE/run_tests.sh${RESET}"
echo "${MAGENTA}  inspect-log : less $LOG_FILE${RESET}"
echo "${MAGENTA}  clean-up    : rm -rf ~/NEXUS-COVE/Logs${RESET}"
exit $EXIT
