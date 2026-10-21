#!/bin/bash
# ============================================================
# run_demo.sh — NEXUS-COVE Interactive Demo Installer
# Version: 2.0.0
# ============================================================

set -uo pipefail

# ─── Globals ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED=$'\033[91m'
GREEN=$'\033[92m'
YELLOW=$'\033[93m'
BLUE=$'\033[94m'
MAGENTA=$'\033[95m'
CYAN=$'\033[96m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

# Default configuration
DEFAULT_MODEL="qwen2.5:0.5b"
DEFAULT_VENV_PRIMARY=".venv-termux"
DEFAULT_VENV_FALLBACK=".venv"
LOG_DIR="./logs"
NON_INTERACTIVE=false
YES_MODE=false
VERBOSE=false
SKIP_PYTHON_DEPS=false
WITH_DEV=false
NO_DEV=false
CUSTOM_VENV=""
CUSTOM_MODEL=""
CUSTOM_LOG_DIR=""

# Runtime state
VENV_PATH=""
PYTHON_BIN=""
PIP_BIN=""
OLLAMA_URL="http://127.0.0.1:11434"
CHOSEN_MODEL=""
PKG_MANAGER=""
PKG_INSTALL_CMD=""

# ─── Logging Infrastructure ─────────────────────────────────
mkdir -p "$LOG_DIR"

log_step_start() {
    local step_name="$1"
    local timestamp
    timestamp=$(date -u +%Y%m%d-%H%M%S)
    LOG_FILE="${LOG_DIR}/${step_name}-${timestamp}.log"
    echo "=== Step: $step_name ===" > "$LOG_FILE"
    echo "=== Started: $(date -u) ===" >> "$LOG_FILE"
    echo "$LOG_FILE"
}

log_step_end() {
    local log_file="$1"
    local exit_code="$2"
    echo "=== Ended: $(date -u) (exit $exit_code) ===" >> "$log_file"
}

run_with_log() {
    local log_file="$1"
    shift
    "$@" >> "$log_file" 2>&1
    return $?
}

# ─── UI Helpers ─────────────────────────────────────────────
detect_ui_tool() {
    if command -v whiptail &>/dev/null; then
        echo "whiptail"
    elif command -v dialog &>/dev/null; then
        echo "dialog"
    else
        echo "read"
    fi
}

UI_TOOL=$(detect_ui_tool)

prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice

    if [[ "$UI_TOOL" == "whiptail" ]]; then
        choice=$(whiptail --title "$title" --menu "" 20 78 10 \
            "${options[@]}" 3>&1 1>&2 2>&3) || return 1
        echo "$choice"
    elif [[ "$UI_TOOL" == "dialog" ]]; then
        choice=$(dialog --title "$title" --menu "" 20 78 10 \
            "${options[@]}" 3>&1 1>&2 2>&3) || return 1
        echo "$choice"
    else
        echo "${BOLD}$title${RESET}" >&2
        local i=1
        for opt in "${options[@]}"; do
            echo "  $i) $opt" >&2
            ((i++))
        done
        echo -n "Select [1-$((i-1))]: " >&2
        read -r choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice < i )); then
            echo "${options[$((choice-1))]}"
        else
            return 1
        fi
    fi
}

prompt_yes_no() {
    local question="$1"
    local default="${2:-n}"
    local answer

    if [[ "$UI_TOOL" == "whiptail" ]]; then
        if [[ "$default" == "y" ]]; then
            whiptail --yesno "$question" 10 60 3>&1 1>&2 2>&3
        else
            whiptail --defaultno --yesno "$question" 10 60 3>&1 1>&2 2>&3
        fi
        return $?
    elif [[ "$UI_TOOL" == "dialog" ]]; then
        if [[ "$default" == "y" ]]; then
            dialog --yesno "$question" 10 60 3>&1 1>&2 2>&3
        else
            dialog --defaultno --yesno "$question" 10 60 3>&1 1>&2 2>&3
        fi
        return $?
    else
        local prompt="[y/N]"
        [[ "$default" == "y" ]] && prompt="[Y/n]"
        echo -n "${BOLD}$question${RESET} $prompt: " >&2
        read -r answer
        answer="${answer:-$default}"
        [[ "$answer" =~ ^[Yy]$ ]]
    fi
}

show_log_and_return() {
    local log_file="$1"
    if [[ -f "$log_file" ]]; then
        if command -v less &>/dev/null; then
            less "$log_file"
        else
            cat "$log_file"
        fi
    else
        echo "Log file not found: $log_file"
    fi
}

# ─── Package Manager Detection ──────────────────────────────
detect_pkg_manager() {
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
        PKG_INSTALL_CMD="apt-get update && apt-get install -y"
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        PKG_INSTALL_CMD="dnf install -y"
    elif command -v yum &>/dev/null; then
        PKG_MANAGER="yum"
        PKG_INSTALL_CMD="yum install -y"
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
        PKG_INSTALL_CMD="pacman -Sy --noconfirm"
    elif command -v apk &>/dev/null; then
        PKG_MANAGER="apk"
        PKG_INSTALL_CMD="apk add --no-cache"
    else
        PKG_MANAGER="unknown"
        PKG_INSTALL_CMD=""
    fi
}

# ─── Error Pattern Matching & Suggestions ───────────────────
suggest_fix_for_error() {
    local log_file="$1"
    local suggestions=()

    if [[ ! -f "$log_file" ]]; then
        return
    fi

    local log_content
    log_content=$(cat "$log_file")

    # Rust / cargo / maturin
    if grep -qiE 'cargo|rustc|maturin|failed to find tool "rustc"' "$log_file"; then
        suggestions+=("Install Rust toolchain: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
    fi

    # Python.h / python3-dev
    if grep -qi 'Python\.h' "$log_file"; then
        case "$PKG_MANAGER" in
            apt) suggestions+=("Install Python headers: $PKG_INSTALL_CMD python3-dev") ;;
            dnf|yum) suggestions+=("Install Python headers: $PKG_INSTALL_CMD python3-devel") ;;
            pacman) suggestions+=("Install Python headers: $PKG_INSTALL_CMD python") ;;
            apk) suggestions+=("Install Python headers: $PKG_INSTALL_CMD python3-dev") ;;
            *) suggestions+=("Install Python development headers for your distribution") ;;
        esac
    fi

    # gcc / cc / make / build tools
    if grep -qiE 'gcc|cc: command not found|make: command not found|build-essential' "$log_file"; then
        case "$PKG_MANAGER" in
            apt) suggestions+=("Install build tools: $PKG_INSTALL_CMD build-essential") ;;
            dnf|yum) suggestions+=("Install build tools: $PKG_INSTALL_CMD gcc make") ;;
            pacman) suggestions+=("Install build tools: $PKG_INSTALL_CMD base-devel") ;;
            apk) suggestions+=("Install build tools: $PKG_INSTALL_CMD build-base") ;;
            *) suggestions+=("Install build tools (gcc, make) for your distribution") ;;
        esac
    fi

    # Network / resolver errors
    if grep -qiE 'connection|timeout|resolve|network|unreachable|Temporary failure' "$log_file"; then
        suggestions+=("Network error detected - check connectivity and retry")
    fi

    # pip / metadata errors
    if grep -qiE 'preparing metadata.*pyproject\.toml|metadata generation failed' "$log_file"; then
        suggestions+=("Try wheel-only install (--only-binary=:all:) to avoid building from source")
    fi

    if [[ ${#suggestions[@]} -gt 0 ]]; then
        echo "${BOLD}${CYAN}Suggested fixes:${RESET}" >&2
        for i in "${!suggestions[@]}"; do
            echo "  $((i+1)). ${suggestions[$i]}" >&2
        done
        echo >&2
    fi
}

# ─── Error Handler ──────────────────────────────────────────
handle_error() {
    local step_name="$1"
    local exit_code="$2"
    local log_file="$3"

    log_step_end "$log_file" "$exit_code"

    if [[ "$step_name" == *"(dev)"* ]]; then
        echo >&2
        echo "${YELLOW}⚠ Optional step failed: $step_name — continuing without it.${RESET}" >&2
        echo "  Log: $log_file" >&2
        echo "  Tip: on Termux, run 'pkg install rust' then re-run with --with-dev" >&2
        echo >&2
        return 5
    fi

    echo >&2
    echo "${RED}${BOLD}❌ Step failed: $step_name (exit $exit_code)${RESET}" >&2
    echo "${CYAN}📄 Log: $log_file${RESET}" >&2
    echo >&2

    suggest_fix_for_error "$log_file"

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        echo "${YELLOW}Non-interactive mode - failing fast.${RESET}" >&2
        cat "$log_file" >&2
        exit "$exit_code"
    fi

    while true; do
        local choice
        choice=$(prompt_menu "Error in $step_name" \
            "1" "View full error log" \
            "2" "Retry step" \
            "3" "Install missing build prerequisites" \
            "4" "Use prebuilt wheels only (--only-binary=:all:)" \
            "5" "Skip optional dependencies and continue degraded" \
            "6" "Abort") || choice="6"

        case "$choice" in
            1)
                show_log_and_return "$log_file"
                ;;
            2)
                return 2  # Signal retry
                ;;
            3)
                if [[ -n "$PKG_INSTALL_CMD" ]]; then
                    echo "${CYAN}Installing build prerequisites...${RESET}" >&2
                    eval "$PKG_INSTALL_CMD" >&2
                    return 2  # Retry after install
                else
                    echo "${RED}No supported package manager detected.${RESET}" >&2
                fi
                ;;
            4)
                return 4  # Signal wheel-only retry
                ;;
            5)
                return 5  # Signal skip optional
                ;;
            6)
                echo "${RED}Aborted by user.${RESET}" >&2
                exit "$exit_code"
                ;;
        esac
    done
}

handle_unexpected_error() {
    local last_cmd="${BASH_COMMAND}"
    local exit_code=$?
    echo >&2
    echo "${RED}${BOLD}❌ Unexpected failure${RESET}" >&2
    echo "${CYAN}Last command: $last_cmd${RESET}" >&2
    echo "${CYAN}Exit code: $exit_code${RESET}" >&2
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "${CYAN}Log: $LOG_FILE${RESET}" >&2
    fi
    exit "$exit_code"
}

trap 'handle_unexpected_error' ERR

# ─── Argument Parsing ───────────────────────────────────────
usage() {
    cat <<EOF
${BOLD}Usage:${RESET} ./run_demo.sh [OPTIONS]

${BOLD}Options:${RESET}
  -y, --yes                 Accept safe defaults, retry once, skip optional deps, never install system packages
  --non-interactive         Force non-interactive mode (fail fast on errors)
  --verbose                 Verbose output
  --log-dir <path>          Log directory (default: ./logs)
  --skip-python-deps        Skip Python dependency installation
  --with-dev                Install dev extras (pytest, ruff, etc.)
  --no-dev                  Explicitly skip dev extras
  --venv <path>             Virtual environment path (default: .venv-termux or .venv)
  --model <name>            Ollama model (default: $DEFAULT_MODEL)
  -h, --help                Show this help

${BOLD}Examples:${RESET}
  ./run_demo.sh                          # Interactive mode
  ./run_demo.sh --yes                    # Automated with safe defaults
  ./run_demo.sh --non-interactive        # CI mode
  ./run_demo.sh --model llama3.2         # Custom model
  ./run_demo.sh --venv /path/to/venv     # Custom venv

${BOLD}Correct launch (not the malformed 'cd NEXUS-COVE ./run_demo.sh ...'):${RESET}
  cd NEXUS-COVE && ./run_demo.sh
  # or
  ./run_demo.sh

${BOLD}Exit codes:${RESET}
  10  Prerequisite failure
  20  Ollama failure
  30  Model download failure
  40  Virtual environment failure
  50  Dependency installation failure
  60  Demo runtime failure
  64  Bad CLI usage
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -y|--yes)
                YES_MODE=true
                NON_INTERACTIVE=true
                NO_DEV=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --log-dir)
                if [[ -z "${2:-}" ]]; then
                    echo "${RED}Error: --log-dir requires a path${RESET}" >&2
                    exit 64
                fi
                CUSTOM_LOG_DIR="$2"
                LOG_DIR="$2"
                mkdir -p "$LOG_DIR"
                shift 2
                ;;
            --skip-python-deps)
                SKIP_PYTHON_DEPS=true
                shift
                ;;
            --with-dev)
                WITH_DEV=true
                NO_DEV=false
                shift
                ;;
            --no-dev)
                NO_DEV=true
                WITH_DEV=false
                shift
                ;;
            --venv)
                if [[ -z "${2:-}" ]]; then
                    echo "${RED}Error: --venv requires a path${RESET}" >&2
                    exit 64
                fi
                CUSTOM_VENV="$2"
                shift 2
                ;;
            --model)
                if [[ -z "${2:-}" ]]; then
                    echo "${RED}Error: --model requires a name${RESET}" >&2
                    exit 64
                fi
                CUSTOM_MODEL="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                echo "${RED}Error: Unknown option: $1${RESET}" >&2
                usage
                exit 64
                ;;
            *)
                # Stray positional argument - likely the malformed cd usage
                echo "${RED}Error: Unexpected positional argument: $1${RESET}" >&2
                echo >&2
                echo "${YELLOW}Did you mean?${RESET}" >&2
                echo "  cd NEXUS-COVE && ./run_demo.sh" >&2
                echo "  # or" >&2
                echo "  ./run_demo.sh" >&2
                exit 64
                ;;
        esac
    done

    # Detect non-interactive mode automatically
    if [[ "$NON_INTERACTIVE" != "true" ]] && (! [[ -t 0 ]] || ! [[ -t 1 ]]); then
        NON_INTERACTIVE=true
        if [[ "$VERBOSE" == "true" ]]; then
            echo "${YELLOW}Non-TTY detected - switching to non-interactive mode${RESET}" >&2
        fi
    fi

    # Model precedence: --model > NEXUS_COVE_MODEL > default
    CHOSEN_MODEL="${CUSTOM_MODEL:-${NEXUS_COVE_MODEL:-$DEFAULT_MODEL}}"
}

# ─── Step Functions ─────────────────────────────────────────
check_prerequisites() {
    local log_file
    log_file=$(log_step_start "prerequisites")

    echo "${CYAN}▶ Checking prerequisites...${RESET}"

    local missing=()

    # Python
    if command -v python3 &>/dev/null; then
        PYTHON_BIN="python3"
    elif command -v python &>/dev/null; then
        PYTHON_BIN="python"
    else
        missing+=("python3")
    fi

    # Pip
    if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
        missing+=("pip")
    fi

    # Ollama
    if ! command -v ollama &>/dev/null; then
        missing+=("ollama")
    fi

    # curl
    if ! command -v curl &>/dev/null; then
        missing+=("curl")
    fi

    # Python version
    if [[ -n "$PYTHON_BIN" ]]; then
        local py_version
        py_version=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [[ "$(echo "$py_version >= 3.11" | bc -l 2>/dev/null || echo 0)" != "1" ]]; then
            missing+=("python >= 3.11 (found $py_version)")
        fi
    fi

    # Build tools (warn only)
    local build_warnings=()
    if ! command -v gcc &>/dev/null && ! command -v cc &>/dev/null; then
        build_warnings+=("gcc/cc")
    fi
    if ! command -v make &>/dev/null; then
        build_warnings+=("make")
    fi
    if ! $PYTHON_BIN -c "import sysconfig; sysconfig.get_config_var('INCLUDEPY')" &>/dev/null; then
        build_warnings+=("python3-dev headers")
    fi

    # Rust (warn only)
    if ! command -v cargo &>/dev/null || ! command -v rustc &>/dev/null; then
        build_warnings+=("rust/cargo (for native extensions)")
    fi

    detect_pkg_manager

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "${RED}Missing required tools:${RESET}" >&2
        for m in "${missing[@]}"; do
            echo "  - $m" >&2
        done
        if [[ -n "$PKG_INSTALL_CMD" ]]; then
            echo "${YELLOW}Install with: $PKG_INSTALL_CMD ${missing[*]}${RESET}" >&2
        fi
        log_step_end "$log_file" 10
        handle_error "prerequisites" 10 "$log_file"
        return $?
    fi

    if [[ ${#build_warnings[@]} -gt 0 && "$VERBOSE" == "true" ]]; then
        echo "${YELLOW}Optional build tools not found:${RESET}"
        for w in "${build_warnings[@]}"; do
            echo "  - $w"
        done
    fi

    echo "${GREEN}✓ Prerequisites satisfied${RESET}"
    log_step_end "$log_file" 0
    return 0
}

start_ollama() {
    local log_file
    log_file=$(log_step_start "ollama")

    echo "${CYAN}▶ Starting Ollama...${RESET}"

    # Check if already running
    if curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        echo "${GREEN}✓ Ollama already running${RESET}"
        log_step_end "$log_file" 0
        return 0
    fi

    echo "Starting Ollama daemon..."
    nohup ollama serve >/dev/null 2>&1 &
    local ollama_pid=$!

    # Wait for health
    local max_wait=30
    local waited=0
    while (( waited < max_wait )); do
        if curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
            echo "${GREEN}✓ Ollama started (PID: $ollama_pid)${RESET}"
            log_step_end "$log_file" 0
            return 0
        fi
        sleep 1
        ((waited++))
    done

    echo "${RED}❌ Ollama failed to start within ${max_wait}s${RESET}"
    log_step_end "$log_file" 20
    handle_error "ollama" 20 "$log_file"
    return $?
}

ensure_model() {
    local log_file
    log_file=$(log_step_start "model-pull")

    echo "${CYAN}▶ Ensuring model: $CHOSEN_MODEL${RESET}"

    # Check if model exists locally
    if ollama list 2>/dev/null | grep -q "^$CHOSEN_MODEL "; then
        echo "${GREEN}✓ Model $CHOSEN_MODEL already present${RESET}"
        log_step_end "$log_file" 0
        return 0
    fi

    echo "Pulling $CHOSEN_MODEL..."
    if run_with_log "$log_file" ollama pull "$CHOSEN_MODEL"; then
        echo "${GREEN}✓ Model pulled successfully${RESET}"
        log_step_end "$log_file" 0
        return 0
    else
        local exit_code=$?
        echo "${RED}❌ Model pull failed${RESET}"
        log_step_end "$log_file" "$exit_code"
        handle_error "model-pull" 30 "$log_file"
        return $?
    fi
}

setup_python_env() {
    local log_file
    log_file=$(log_step_start "venv")

    echo "${CYAN}▶ Setting up Python environment...${RESET}"

    # Determine venv path
    if [[ -n "$CUSTOM_VENV" ]]; then
        VENV_PATH="$CUSTOM_VENV"
    elif [[ -d "$DEFAULT_VENV_PRIMARY" ]]; then
        VENV_PATH="$DEFAULT_VENV_PRIMARY"
    else
        VENV_PATH="$DEFAULT_VENV_FALLBACK"
    fi

    # Create venv if needed
    if [[ ! -d "$VENV_PATH" ]]; then
        echo "Creating virtual environment at $VENV_PATH..."
        if ! run_with_log "$log_file" "$PYTHON_BIN" -m venv "$VENV_PATH"; then
            local exit_code=$?
            echo "${RED}❌ Failed to create virtual environment${RESET}"
            log_step_end "$log_file" "$exit_code"
            handle_error "venv" 40 "$log_file"
            return $?
        fi
    else
        echo "${GREEN}✓ Reusing existing venv: $VENV_PATH${RESET}"
    fi

    # Activate and upgrade
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate"

    PIP_BIN="$VENV_PATH/bin/pip"
    PYTHON_BIN="$VENV_PATH/bin/python"

    echo "Upgrading pip, setuptools, wheel..."
    if ! run_with_log "$log_file" "$PIP_BIN" install --upgrade pip setuptools wheel; then
        local exit_code=$?
        echo "${RED}❌ Failed to upgrade pip/setuptools/wheel${RESET}"
        log_step_end "$log_file" "$exit_code"
        handle_error "venv" 40 "$log_file"
        return $?
    fi

    echo "${GREEN}✓ Python environment ready${RESET}"
    log_step_end "$log_file" 0
    return 0
}

install_python_deps() {
    [[ "$SKIP_PYTHON_DEPS" == "true" ]] && return 0

    local log_file
    log_file=$(log_step_start "python-deps")

    echo "${CYAN}▶ Installing Python dependencies...${RESET}"

    # Core dependencies first (from pyproject.toml: websockets)
    # Note: aiohttp is required by the demo test script
    local core_deps=("websockets>=16,<17" "aiohttp>=3.9,<4")
    local dev_extras=("pytest>=8,<9" "pytest-asyncio>=0.24,<1" "ruff>=0.6,<1" "coverage[toml]>=7,<8" "pre-commit>=3,<5")

    local use_wheel_only=true
    local skipped_optional=false

    # Install core deps
    echo "Installing core dependencies: ${core_deps[*]}"
    while true; do
        if [[ "$use_wheel_only" == "true" ]]; then
            echo "Trying wheel-only install (--only-binary=:all:)..."
            if run_with_log "$log_file" "$PIP_BIN" install --only-binary=:all: "${core_deps[@]}"; then
                echo "${GREEN}✓ Core dependencies installed (wheel-only)${RESET}"
                break
            else
                local exit_code=$?
                echo "${YELLOW}Wheel-only install failed, trying normal install...${RESET}"
                use_wheel_only=false
                # If YES_MODE, we don't prompt - just continue to normal install
                if [[ "$YES_MODE" == "true" ]]; then
                    continue
                fi
                local choice
                handle_error "python-deps (core)" "$exit_code" "$log_file"
                choice=$?
                case "$choice" in
                    2) continue ;;  # retry
                    4) use_wheel_only=true; continue ;;  # wheel-only
                    5)
                        # Skip optional - but core is required, so this is abort for core
                        echo "${RED}Core dependencies are required. Cannot skip.${RESET}"
                        ;;
                    *) exit "$exit_code" ;;
                esac
            fi
        else
            if run_with_log "$log_file" "$PIP_BIN" install "${core_deps[@]}"; then
                echo "${GREEN}✓ Core dependencies installed${RESET}"
                break
            else
                local exit_code=$?
                if [[ "$YES_MODE" == "true" ]]; then
                    # In yes mode, we've already tried both - fail
                    log_step_end "$log_file" "$exit_code"
                    handle_error "python-deps (core)" "$exit_code" "$log_file"
                    return $?
                fi
                local choice
                handle_error "python-deps (core)" "$exit_code" "$log_file"
                choice=$?
                case "$choice" in
                    2) continue ;;
                    4) use_wheel_only=true; continue ;;
                    *) exit "$exit_code" ;;
                esac
            fi
        fi
    done

    # Install dev extras (optional)
    if [[ "$NO_DEV" != "true" && "$WITH_DEV" == "true" ]] || [[ "$NO_DEV" != "true" && "$WITH_DEV" != "true" && "$YES_MODE" != "true" ]]; then
        # In interactive mode without --no-dev, ask
        if [[ "$YES_MODE" != "true" && "$WITH_DEV" != "true" ]]; then
            if prompt_yes_no "Install dev extras (pytest, ruff, etc.)?" "n"; then
                WITH_DEV=true
            else
                NO_DEV=true
            fi
        fi

        if [[ "$WITH_DEV" == "true" ]]; then
            echo "Installing dev extras..."
            while true; do
                if [[ "$use_wheel_only" == "true" ]]; then
                    if run_with_log "$log_file" "$PIP_BIN" install --only-binary=:all: "${dev_extras[@]}"; then
                        echo "${GREEN}✓ Dev extras installed (wheel-only)${RESET}"
                        break
                    else
                        local exit_code=$?
                        echo "${YELLOW}Wheel-only install failed for dev extras, trying normal...${RESET}"
                        use_wheel_only=false
                        if [[ "$YES_MODE" == "true" ]]; then
                            continue
                        fi
                        local choice
                        handle_error "python-deps (dev)" "$exit_code" "$log_file"
                        choice=$?
                        case "$choice" in
                            2) continue ;;
                            4) use_wheel_only=true; continue ;;
                            5)
                                echo "${YELLOW}Skipping dev extras (continuing degraded)${RESET}"
                                skipped_optional=true
                                break
                                ;;
                            *) exit "$exit_code" ;;
                        esac
                    fi
                else
                    if run_with_log "$log_file" "$PIP_BIN" install "${dev_extras[@]}"; then
                        echo "${GREEN}✓ Dev extras installed${RESET}"
                        break
                    else
                        local exit_code=$?
                        if [[ "$YES_MODE" == "true" ]]; then
                            echo "${YELLOW}Dev extras failed - skipping (continuing degraded)${RESET}"
                            skipped_optional=true
                            break
                        fi
                        local choice
                        handle_error "python-deps (dev)" "$exit_code" "$log_file"
                        choice=$?
                        case "$choice" in
                            2) continue ;;
                            4) use_wheel_only=true; continue ;;
                            5)
                                echo "${YELLOW}Skipping dev extras (continuing degraded)${RESET}"
                                skipped_optional=true
                                break
                                ;;
                            *) exit "$exit_code" ;;
                        esac
                    fi
                fi
            done
        fi
    fi

    if [[ "$skipped_optional" == "true" ]]; then
        echo "${YELLOW}⚠ Continuing without dev extras${RESET}"
    fi

    echo "${GREEN}✓ Python dependencies complete${RESET}"
    log_step_end "$log_file" 0
    return 0
}

run_demo() {
    local log_file
    log_file=$(log_step_start "demo")

    echo "${CYAN}▶ Running demo test...${RESET}"
    echo "${CYAN}Model: $CHOSEN_MODEL${RESET}"

    # Run the test script with the chosen model
    if run_with_log "$log_file" "$PYTHON_BIN" tests/termux_ollama_test.py; then
        echo "${GREEN}${BOLD}✅ Demo completed successfully!${RESET}"
        log_step_end "$log_file" 0
        return 0
    else
        local exit_code=$?
        echo "${RED}❌ Demo test failed${RESET}"
        log_step_end "$log_file" "$exit_code"
        handle_error "demo" 60 "$log_file"
        return $?
    fi
}

# ─── Main ───────────────────────────────────────────────────
main() {
    echo "${BOLD}${CYAN}=== NEXUS-COVE Interactive Demo Installer ===${RESET}"
    echo

    parse_args "$@"

    echo "${BOLD}Configuration:${RESET}"
    echo "  Model: $CHOSEN_MODEL"
    echo "  Venv:  $VENV_PATH"
    echo "  Logs:  $LOG_DIR"
    echo "  Interactive: $([[ "$NON_INTERACTIVE" == "true" ]] && echo "no" || echo "yes")"
    echo "  Dev extras: $([[ "$NO_DEV" == "true" ]] && echo "no" || echo "yes")"
    echo

    # Run steps
    check_prerequisites || exit $?
    start_ollama || exit $?
    ensure_model || exit $?
    setup_python_env || exit $?
    install_python_deps || exit $?
    run_demo || exit $?

    echo
    echo "${GREEN}${BOLD}=== All steps completed successfully ===${RESET}"
    echo "${CYAN}Logs saved to: $LOG_DIR${RESET}"
}

main "$@"