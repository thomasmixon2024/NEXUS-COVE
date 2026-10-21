#!/usr/bin/env bash
# Launch the full NEXUS-COVE test bed: server, manager, 3 workers, static server, browser.
#   ./cove-testbed.sh              test backend (canned replies)
#   ./cove-testbed.sh --model      real Ollama chat replies
#   ./cove-testbed.sh --no-browser headless
set -uo pipefail
cd "$(dirname "$0")" || exit 1

URI="ws://127.0.0.1:8765"
HTTP_PORT=8080
MODEL_FLAG=""
OPEN_BROWSER=1
for arg in "$@"; do
    case "$arg" in
        --model) MODEL_FLAG="--model qwen2.5:0.5b" ;;
        --no-browser) OPEN_BROWSER=0 ;;
    esac
done

mkdir -p logs data .pids

[ -x .venv/bin/cove-server ] || {
    echo "ERROR: .venv/bin/cove-server missing"
    echo "  Run: .venv/bin/pip install -e ."
    exit 1
}

# Clean slate
if pgrep -f 'cove-server|cove-manager|cove-worker|http.server 8080' >/dev/null 2>&1; then
    echo "Cleaning up previous run..."
    pkill -f 'cove-server|cove-manager|cove-worker|http.server 8080' 2>/dev/null || true
    sleep 1
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

echo "=== NEXUS-COVE test bed ==="

start_one server cove-server
wait_for_log server "listening\|Listening\|8765" 5 || {
    echo "ERROR: server failed to start"
    tail -15 logs/server.log
    exit 1
}

start_one manager cove-manager --uri "$URI" --db data/cove.db
wait_for_log manager "connected" 5 || {
    echo "ERROR: manager failed to connect"
    tail -15 logs/manager.log
    exit 1
}

for w in Aegis-Worker Elon-Worker Vigil-Worker; do
    start_one "$w" cove-worker --name "$w" --uri "$URI" --test-backend $MODEL_FLAG
done
sleep 1.5

# Static server for the browser UI
if ! pgrep -f "http.server $HTTP_PORT" >/dev/null 2>&1; then
    (python3 -m http.server "$HTTP_PORT" --bind 127.0.0.1 > logs/static.log 2>&1 &)
    sleep 1
    echo "  + static server (127.0.0.1:$HTTP_PORT)"
fi

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
