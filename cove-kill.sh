#!/bin/bash
# cove-kill.sh — Stop all NEXUS COVE processes and free ports
# Usage: ./cove-kill.sh

set -uo pipefail

# Colors
RED=$'\033[91m'
GREEN=$'\033[92m'
YELLOW=$'\033[93m'
BLUE=$'\033[94m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

echo "${BOLD}${BLUE}=== Stopping NEXUS COVE ===${RESET}"

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "${YELLOW}Killing processes on port $port: $pids${RESET}"
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
        # Verify
        local remaining
        remaining=$(lsof -ti:"$port" 2>/dev/null || true)
        if [[ -n "$remaining" ]]; then
            echo "${RED}Warning: Port $port still in use by: $remaining${RESET}"
        else
            echo "${GREEN}✓ Port $port freed${RESET}"
        fi
    else
        echo "${GREEN}✓ Port $port already free${RESET}"
    fi
}

# Kill processes by name pattern
kill_by_name() {
    local pattern=$1
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        echo "${YELLOW}Killing $pattern processes: $pids${RESET}"
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
    fi
}

# Main cleanup
echo "${BLUE}Freeing ports...${RESET}"
kill_port 8765  # WebSocket server
kill_port 8080  # Static file server

echo "${BLUE}Stopping NEXUS COVE processes...${RESET}"
kill_by_name "nexus_cove.transport.websocket.server"
kill_by_name "nexus_cove.orchestration.manager"
kill_by_name "nexus_cove.agents.worker"
kill_by_name "http.server 8080"

echo
echo "${GREEN}${BOLD}=== NEXUS COVE stopped ===${RESET}"