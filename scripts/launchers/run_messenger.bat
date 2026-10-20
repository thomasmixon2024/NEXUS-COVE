@echo off
title NEXUS COVE Messenger - 3 Way Communication Test
echo Starting NEXUS COVE 3-way communication test...
echo.

REM Create data directory if it doesn't exist
if not exist data mkdir data

REM Start WebSocket Server in a new window
echo Starting WebSocket Server...
start "NEXUS COVE WebSocket Server" cmd /k "python -m nexus_cove.transport.websocket.server"

REM Wait a moment for server to start
timeout /t 2 > nul

REM Start Manager in a new window
echo Starting Manager...
start "NEXUS COVE Manager" cmd /k "python -m nexus_cove.orchestration.manager"

REM Wait a moment for manager to connect
timeout /t 2 > nul

REM Start First Worker in a new window
echo Starting Worker 1 (Aegis-Worker)...
start "NEXUS COVE Worker 1" cmd /k "python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend"

REM Wait a moment
timeout /t 2 > nul

REM Start Second Worker in a new window
echo Starting Worker 2 (Vigil-Worker)...
start "NEXUS COVE Worker 2" cmd /k "python -m nexus_cove.agents.worker --name Vigil-Worker --capability general --capability analysis --test-backend"

echo.
echo All components started! Check the individual windows for communication logs.
echo.
echo To test the communication:
echo 1. In the Manager window, you should see worker registrations
echo 2. You can manually submit tasks via the manager (would need to modify code for direct input)
echo 3. Workers will process tasks and send results back
echo 4. All communication flows through the WebSocket server on ws://127.0.0.1:8765
echo.
pause