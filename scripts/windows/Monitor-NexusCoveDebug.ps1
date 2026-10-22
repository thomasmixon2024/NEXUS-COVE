# ==========================================
# NEXUS-COVE ADVANCED DIAGNOSTIC & MONITOR
# ==========================================
$ErrorActionPreference = "SilentlyContinue"
$WebSocketPort = 8765$OllamaPort = 11434 # Common local LLM port (change if using a custom proxy/gateway)
$LogDir = "logs"

# Ensure log directory exists
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

Write-Output "==================================================="
Write-Output " [1] CHECKING LOCAL LLM BACKEND & PROXY PORTS"
Write-Output "==================================================="

# Check WebSocket Server Port
$WsConn = Get-NetTCPConnection -LocalPort$WebSocketPort -State Listen -ErrorAction SilentlyContinue
if ($WsConn) {
    Write-Output "[SUCCESS] WebSocket Server port ($WebSocketPort) is active."
} else {
    Write-Output "[CRITICAL] WebSocket port ($WebSocketPort) is NOT listening. Run server.py first."
}

# Check Local LLM/Ollama/Proxy Port
$LlmConn = Get-NetTCPConnection -LocalPort$OllamaPort -State Listen -ErrorAction SilentlyContinue
if ($LlmConn) {
    Write-Output "[SUCCESS] Local LLM gateway/Ollama port ($OllamaPort) is listening."
} else {
    Write-Output "[WARNING] Port $OllamaPort is closed. If you use Ollama or a local proxy, ensure it is running!"
}

Write-Output "`n==================================================="
Write-Output " [2] INSPECTING ACTIVE PYTHON AGENT PROCESSES"
Write-Output "==================================================="

$PythonProcs = Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'"
if ($PythonProcs) {
    Write-Output "Found active Python runtimes:"
    $PythonProcs | Select-Object ProcessId, CommandLine | Format-Table -AutoSize
} else {
    Write-Output "[ALERT] No active Python processes found."
}

Write-Output "`n==================================================="
Write-Output " [3] LAUNCHING MONITORED TEST RUN & CAPTURING LOGS"
Write-Output "==================================================="

Write-Output "Starting server and agents with stream redirection..."

# Start Server and log output
Start-Process python -ArgumentList "server.py" -NoNewWindow -RedirectStandardOutput "$LogDir\server_out.log" -RedirectStandardError "$LogDir\server_err.log"
Start-Sleep -Seconds 2

# Start Aegis-Worker with logging
Start-Process python -ArgumentList "agent_client.py --name Aegis-Worker --role ""Methodical builder focused on structural integrity and trust-building.""" -NoNewWindow -RedirectStandardOutput "$LogDir\aegis_out.log" -RedirectStandardError "$LogDir\aegis_err.log"

# Start Vigil-Worker with logging
Start-Process python -ArgumentList "agent_client.py --name Vigil-Worker --role ""Playful observer interested in behavioral patterns and story structures.""" -NoNewWindow -RedirectStandardOutput "$LogDir\vigil_out.log" -RedirectStandardError "$LogDir\vigil_err.log"

Write-Output "Processes spawned. Monitoring live error logs for 15 seconds..."
Write-Output "Tip: Check the 'logs/' folder if agents report LLM unavailability."

$StopWatch = [System.Diagnostics.Stopwatch]::StartNew()
while ($StopWatch.Elapsed.Seconds -lt 15) {
    Clear-Host
    Write-Output "=== LIVE LOG TAIL (Aegis & Vigil Error Streams) ==="
    if (Test-Path "$LogDir\aegis_err.log") {
        Write-Output "--- Aegis Errors ---"
        Get-Content "$LogDir\aegis_err.log" -Tail 3
    }
    if (Test-Path "$LogDir\vigil_err.log") {
        Write-Output "--- Vigil Errors ---"
        Get-Content "$LogDir\vigil_err.log" -Tail 3
    }
    Start-Sleep -Seconds 3
}
$StopWatch.Stop()
