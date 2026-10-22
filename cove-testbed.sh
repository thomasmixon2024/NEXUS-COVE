#!/usr/bin/env bash
# Launch the full NEXUS-COVE test bed with Ollama + model as mandatory processes.
# Startup order: Ollama server -> Model -> WebSocket server -> Manager -> Workers -> Static server -> Browser
#   ./cove-testbed.sh                  real AI (Ollama + model mandatory)
#   ./cove-testbed.sh --model NAME     specify model (default: qwen2.5:0.5b)
#   ./cove-testbed.sh --agent NAME     specify agent personality (default: all three)
#   ./cove-testbed.sh --no-browser     headless
#   ./cove-testbed.sh --test-backend   use canned replies (no Ollama)
set -uo pipefail
cd "$(dirname "$0")" || exit 1

URI="ws://127.0.0.1:8765"
HTTP_PORT=8080
MODEL_NAME="qwen2.5:0.5b"
OPEN_BROWSER=1
SELECTED_AGENT=""
USE_TEST_BACKEND=0

for arg in "$@"; do
    case "$arg" in
        --model)
            shift
            if [ $# -gt 0 ] && [[ ! "$1" =~ ^-- ]]; then
                MODEL_NAME="$1"
            fi
            ;;
        --agent)
            shift
            if [ $# -gt 0 ] && [[ ! "$1" =~ ^-- ]]; then
                SELECTED_AGENT="$1"
            fi
            ;;
        --no-browser) OPEN_BROWSER=0 ;;
        --test-backend) USE_TEST_BACKEND=1 ;;
    esac
done

mkdir -p logs data .pids

[ -x .venv/bin/cove-server ] || {
    echo "ERROR: .venv/bin/cove-server missing"
    echo "  Run: .venv/bin/pip install -e ."
    exit 1
}

# Clean slate
if pgrep -f 'cove-server|cove-manager|cove-worker|nexus_cove.transport.websocket.server|http.server 8080|ollama serve' >/dev/null 2>&1; then
    echo "Cleaning up previous run..."
    pkill -f 'cove-server|cove-manager|cove-worker|nexus_cove.transport.websocket.server|http.server 8080|ollama serve' 2>/dev/null || true
    sleep 1
fi

echo "=== NEXUS-COVE test bed ==="

# Step 1: Start Ollama server (mandatory unless --test-backend)
if [ "$USE_TEST_BACKEND" -eq 0 ]; then
    echo "Starting Ollama server..."
    ollama serve > logs/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo $OLLAMA_PID > .pids/ollama.pid
    # Wait for Ollama to be ready
    for i in {1..30}; do
        if curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null; then
            echo "  Ollama server started (pid $OLLAMA_PID)"
            break
        fi
        sleep 0.5
    done
    if ! curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null; then
        echo "❌ Failed to start Ollama server"
        exit 1
    fi

    # Step 2: Ensure model is available
    echo "Ensuring model $MODEL_NAME is available..."
    if ! curl -s http://127.0.0.1:11434/api/tags | grep -q "\"name\":\"$MODEL_NAME\""; then
        echo "Pulling model $MODEL_NAME..."
        ollama pull "$MODEL_NAME"
    fi
    echo "  Model $MODEL_NAME ready"
    MODEL_FLAG="--model $MODEL_NAME"
else
    echo "Using test backend (canned replies)"
    MODEL_FLAG=""
fi

start_one() {
    local name="$1"; shift
    : > "logs/$name.log"
    .venv/bin/"$@" >> "logs/$name.log" 2>&1 &
    echo $! > ".pids/$name.pid"
    echo "  + $name (pid $!)"
}

wait_for_log() {
    local name="$1" pattern="$2" timeout="${3:-8}"
    local i=0
    while [ $i -lt $((timeout * 10)) ]; do
        grep -q "$pattern" "logs/$name.log" 2>/dev/null && return 0
        sleep 0.1
        i=$((i+1))
    done
    return 1
}

# Step 3: Start WebSocket server
start_one server cove-server
wait_for_log server "listening\|Listening\|8765" 5 || {
    echo "ERROR: server failed to start"
    tail -15 logs/server.log
    exit 1
}

# Step 4: Start Manager
start_one manager cove-manager --uri "$URI" --db data/cove.db
wait_for_log manager "connected" 5 || {
    echo "ERROR: manager failed to connect"
    tail -15 logs/manager.log
    exit 1
}

# Step 5: Start Workers
if [ -n "$SELECTED_AGENT" ]; then
    WORKERS=("$SELECTED_AGENT")
else
    WORKERS=(Aegis-Worker Elon-Worker Vigil-Worker)
fi

for w in "${WORKERS[@]}"; do
    if [ "$USE_TEST_BACKEND" -eq 0 ]; then
        # Use test backend for task execution + real AI (Ollama) for chat replies
        start_one "$w" cove-worker --name "$w" --uri "$URI" --personality "$w" --test-backend $MODEL_FLAG
    else
        # Use test backend with canned replies only
        start_one "$w" cove-worker --name "$w" --uri "$URI" --test-backend
    fi
done
sleep 1.5

# Step 6: Static server for the browser UI
if ! pgrep -f "http.server $HTTP_PORT" >/dev/null 2>&1; then
    (python3 -m http.server "$HTTP_PORT" --bind 127.0.0.1 > logs/static.log 2>&1 &)
    sleep 1
    echo "  + static server (127.0.0.1:$HTTP_PORT)"
fi

# Step 7: Launch HTML in browser (at the very end)
URL="http://127.0.0.1:$HTTP_PORT/web/index.html"
echo
echo "Dashboard: $URL"

if [ "$OPEN_BROWSER" -eq 1 ]; then
    am start -a android.intent.action.VIEW -d "$URL" -p com.android.chrome >/dev/null 2>&1 \
      || am start -a android.intent.action.VIEW -d "$URL" -p com.microsoft.emmx >/dev/null 2>&1 \
      || termux-open-url "$URL" 2>/dev/null \
      || echo "  Open manually: $URL"
fi

echo
echo "Stop:   ./cove-kill.sh"
echo "Logs:   tail -f logs/*.log"
