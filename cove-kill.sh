#!/usr/bin/env bash
# Kill every NEXUS-COVE process and free the ports. Idempotent — safe to run when nothing is up.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "=== Stopping NEXUS-COVE ==="

for pat in cove-worker cove-manager cove-server "nexus_cove.transport.websocket.server" "ollama serve"; do
    pids=$(pgrep -f "$pat" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null || true
        sleep 0.3
        still=$(pgrep -f "$pat" 2>/dev/null || true)
        [ -n "$still" ] && kill -9 $still 2>/dev/null || true
        echo "  x $pat"
    else
        echo "  . $pat not running"
    fi
done

# Kill whatever still holds the WS port
if command -v ss >/dev/null 2>&1; then
    holders=$(ss -ltnp 2>/dev/null | grep ':8765' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
    if [ -n "$holders" ]; then
        kill $holders 2>/dev/null || true
        sleep 0.3
        kill -9 $holders 2>/dev/null || true
        echo "  x port 8765 ($holders)"
    fi
fi

# Kill whatever still holds the Ollama port
if command -v ss >/dev/null 2>&1; then
    holders=$(ss -ltnp 2>/dev/null | grep ':11434' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
    if [ -n "$holders" ]; then
        kill $holders 2>/dev/null || true
        sleep 0.3
        kill -9 $holders 2>/dev/null || true
        echo "  x port 11434 ($holders)"
    fi
fi

# Kill static server
holders=$(pgrep -f 'http.server 8080' 2>/dev/null || true)
if [ -n "$holders" ]; then
    kill $holders 2>/dev/null || true
    echo "  x http.server on 8080"
fi

rm -f .pids/*.pid 2>/dev/null || true

sleep 0.5
remaining=$(pgrep -af 'cove-server|cove-manager|cove-worker|http.server 8080|ollama serve' 2>/dev/null || true)
if [ -n "$remaining" ]; then
    echo
    echo "WARNING: still running:"
    echo "$remaining"
else
    echo
    echo "OK - all stopped, ports free."
fi
