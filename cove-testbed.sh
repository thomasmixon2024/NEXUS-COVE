#!/bin/bash
# cove-testbed.sh — One-command launch of NEXUS COVE stack + browser dashboard
# Usage: ./cove-testbed.sh

set -uo pipefail

# Colors
RED=$'\033[91m'
GREEN=$'\033[92m'
YELLOW=$'\033[93m'
BLUE=$'\033[94m'
MAGENTA=$'\033[95m'
CYAN=$'\033[96m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

# Configuration
MODEL="qwen2.5:0.5b"
OLLAMA_URL="http://127.0.0.1:11434"
WS_PORT=8765
HTTP_PORT=8080
WS_URI="ws://127.0.0.1:$WS_PORT"
LOG_DIR="./logs"

# PIDs for cleanup
SERVER_PID=""
MANAGER_PID=""
WORKER_PIDS=()
HTTP_PID=""

# Cleanup function
cleanup() {
    echo
    echo "${YELLOW}Cleaning up...${RESET}"
    [[ -n "$HTTP_PID" ]] && kill "$HTTP_PID" 2>/dev/null || true
    for pid in "${WORKER_PIDS[@]}"; do
        [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    done
    [[ -n "$MANAGER_PID" ]] && kill "$MANAGER_PID" 2>/dev/null || true
    [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
    # Also kill by port as backup
    lsof -ti:$WS_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:$HTTP_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Logging
mkdir -p "$LOG_DIR"

log_step() {
    echo "${CYAN}▶ $1${RESET}"
}

log_ok() {
    echo "${GREEN}✓ $1${RESET}"
}

log_err() {
    echo "${RED}✗ $1${RESET}"
}

wait_for_port() {
    local port=$1
    local name=$2
    local timeout=${3:-10}
    local count=0
    while (( count < timeout )); do
        if lsof -ti:"$port" >/dev/null 2>&1; then
            log_ok "$name listening on port $port"
            return 0
        fi
        sleep 1
        ((count++))
    done
    log_err "$name failed to start on port $port within ${timeout}s"
    return 1
}

wait_for_ws() {
    local timeout=${1:-10}
    local count=0
    while (( count < timeout )); do
        if python3 -c "
import asyncio, websockets, sys
async def test():
    try:
        async with websockets.connect('$WS_URI', open_timeout=2) as ws:
            await ws.send('{\"version\":1,\"action\":\"register\",\"agent_id\":\"test\",\"capabilities\":[\"general\"]}')
            await asyncio.wait_for(ws.recv(), timeout=2)
            return True
    except: return False
print('ok' if asyncio.run(test()) else 'fail')
" 2>/dev/null | grep -q "ok"; then
            log_ok "WebSocket server ready"
            return 0
        fi
        sleep 1
        ((count++))
    done
    log_err "WebSocket server not ready within ${timeout}s"
    return 1
}

wait_for_ollama() {
    local timeout=${1:-30}
    local count=0
    while (( count < timeout )); do
        if curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
            log_ok "Ollama daemon reachable"
            return 0
        fi
        sleep 1
        ((count++))
    done
    log_err "Ollama not reachable within ${timeout}s"
    return 1
}

ensure_model() {
    if ollama list 2>/dev/null | grep -q "^$MODEL "; then
        log_ok "Model $MODEL already present"
        return 0
    fi
    log_step "Pulling model $MODEL..."
    if ollama pull "$MODEL" >/dev/null 2>&1; then
        log_ok "Model $MODEL pulled"
        return 0
    else
        log_err "Failed to pull model $MODEL"
        return 1
    fi
}

# Main
echo "${BOLD}${MAGENTA}=== NEXUS COVE Testbed Launcher ===${RESET}"
echo

# 1. Check prerequisites
log_step "Checking prerequisites..."
for cmd in python3 ollama curl lsof; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_err "Missing required command: $cmd"
        exit 1
    fi
done
log_ok "All commands available"

# 2. Start Ollama if needed
log_step "Ensuring Ollama daemon..."
if ! curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    echo "Starting Ollama..."
    nohup ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
    sleep 2
fi
wait_for_ollama || exit 1

# 3. Ensure model
ensure_model || exit 1

# 4. Activate venv
log_step "Activating Python environment..."
if [[ -d ".venv-termux" ]]; then
    source .venv-termux/bin/activate
elif [[ -d ".venv" ]]; then
    source .venv/bin/activate
else
    log_err "No virtual environment found. Run run_demo.sh first."
    exit 1
fi
log_ok "Python environment activated"

# 5. Kill any existing processes on our ports
log_step "Cleaning up existing processes..."
lsof -ti:$WS_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
lsof -ti:$HTTP_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
sleep 1
log_ok "Ports cleared"

# 6. Start WebSocket server
log_step "Starting WebSocket server on port $WS_PORT..."
cd "$(dirname "$0")"
nohup python -m nexus_cove.transport.websocket.server >"$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!
wait_for_port $WS_PORT "WebSocket server" 10 || exit 1
wait_for_ws 10 || exit 1

# 7. Start Manager
log_step "Starting Manager..."
nohup python -m nexus_cove.orchestration.manager --uri "$WS_URI" --db data/cove.db >"$LOG_DIR/manager.log" 2>&1 &
MANAGER_PID=$!
sleep 2
# Wait for manager to register (it logs "manager connected")
local count=0
while (( count < 10 )); do
    if grep -q "manager connected" "$LOG_DIR/manager.log" 2>/dev/null; then
        log_ok "Manager connected"
        break
    fi
    sleep 1
    ((count++))
done
if (( count >= 10 )); then
    log_err "Manager failed to connect"
    exit 1
fi

# 8. Start Workers with conversational model
log_step "Starting 3 workers with --model $MODEL..."
WORKER_NAMES=("Aegis-Worker" "Vigil-Worker" "Elon-Worker")
for name in "${WORKER_NAMES[@]}"; do
    nohup python -m nexus_cove.agents.worker \
        --name "$name" \
        --test-backend \
        --model "$MODEL" \
        --ollama-url "$OLLAMA_URL" \
        --uri "$WS_URI" \
        >"$LOG_DIR/${name}.log" 2>&1 &
    WORKER_PIDS+=($!)
    sleep 0.5
done

# Wait for workers to register
log_step "Waiting for workers to register..."
count=0
while (( count < 15 )); do
    registered=0
    for name in "${WORKER_NAMES[@]}"; do
        if grep -q "agent registered.*$name" "$LOG_DIR/manager.log" 2>/dev/null; then
            ((registered++))
        fi
    done
    if (( registered >= 3 )); then
        log_ok "All 3 workers registered"
        break
    fi
    sleep 1
    ((count++))
done
if (( count >= 15 )); then
    log_err "Not all workers registered within 15s"
    exit 1
fi

# 9. Start static file server for web UI
log_step "Starting static file server on port $HTTP_PORT..."
cd web
nohup python -m http.server $HTTP_PORT >"$LOG_DIR/http.log" 2>&1 &
HTTP_PID=$!
cd ..
wait_for_port $HTTP_PORT "HTTP server" 5 || exit 1

# 10. Open browser
echo
log_ok "All services started!"
echo "${BOLD}${GREEN}=== NEXUS COVE Testbed Ready ===${RESET}"
echo
echo "  Dashboard: ${CYAN}http://127.0.0.1:$HTTP_PORT${RESET}"
echo "  WebSocket: ${CYAN}$WS_URI${RESET}"
echo "  Model:     ${CYAN}$MODEL${RESET}"
echo "  Logs:      ${CYAN}$LOG_DIR/${RESET}"
echo

# Try to open browser
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:$HTTP_PORT" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:$HTTP_PORT" >/dev/null 2>&1 &
elif command -v termux-open-url >/dev/null 2>&1; then
    termux-open-url "http://127.0.0.1:$HTTP_PORT" >/dev/null 2>&1 &
else
    echo "${YELLOW}Open http://127.0.0.1:$HTTP_PORT in your browser${RESET}"
fi

echo
echo "${BOLD}Press Ctrl+C to stop all services${RESET}"
echo

# Keep running until interrupted
wait