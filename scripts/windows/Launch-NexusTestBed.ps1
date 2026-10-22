# =====================================================================
# Launch-NexusTestBed.ps1
# Starts the NEXUS COVE test bed silently: WebSocket server, manager,
# and two workers run as hidden processes. Their output goes to files
# in <repo>\logs\. The browser GUI (web\index.html) opens at the end.
#
# Run with:  powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File scripts\launchers\Launch-NexusTestBed.ps1
#
# The server is started only if the port is free, so running the
# launcher twice does not create a second server.
#
# Logs:  logs\server.out.log, logs\manager.out.log, logs\Aegis-Worker.out.log, ...
# Stop:  see docs\operations\development.md (stop nexus_cove processes)
# =====================================================================
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$logDir   = Join-Path $repoRoot 'logs'
$htmlPath = Join-Path $repoRoot 'web\index.html'
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$port     = 8765
$uri      = "ws://127.0.0.1:$port"
$ollamaUrl = 'http://127.0.0.1:11434'
$modelName = 'qwen2.5:0.5b'
$launchLog = Join-Path $logDir 'launcher.log'

function Write-LaunchLog {
    param([string]$Level, [string]$Message)
    $line = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Add-Content -LiteralPath $launchLog -Value $line -Encoding UTF8
}

function Test-AgentRunning {
    param([string]$Needle)
    $hit = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*$Needle*" }
    return [bool]$hit
}

function Get-WorkerProcesses {
    param([string]$AgentName)
    $namePattern = '--name\s+"?' + [regex]::Escape($AgentName) + '"?(\s|$)'
    return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
            $_.CommandLine -match 'nexus_cove\.agents\.worker' -and
            $_.CommandLine -match $namePattern
        })
}

function Start-Hidden {
    param([string]$Name, [string[]]$ArgList, [string]$ExecutablePath)
    if (-not $ExecutablePath) { $ExecutablePath = $pythonExe }
    $out = Join-Path $logDir ("{0}.out.log" -f $Name)
    $err = Join-Path $logDir ("{0}.err.log" -f $Name)
    Start-Process -FilePath $ExecutablePath -ArgumentList (@('-u') + $ArgList) `
        -WorkingDirectory $repoRoot -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
    Write-LaunchLog 'INFO' "Started $Name (logs: $out)"
}

function Ensure-Worker {
    param([string]$AgentName, [string[]]$ArgList)
    $existing = @(Get-WorkerProcesses $AgentName)
    if ($existing.Count -gt 0) {
        $wrongModel = @($existing | Where-Object {
            $_.CommandLine -notmatch ('--model\s+' + [regex]::Escape($modelName) + '(\s|$)')
        })
        if ($wrongModel.Count -eq 0) {
            Write-LaunchLog 'INFO' "$AgentName already running with $modelName; not starting another."
            return
        }

        Write-LaunchLog 'WARN' "$AgentName has a stale model configuration; restarting it with $modelName."
        foreach ($process in $existing) {
            Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
        }
        for ($i = 0; $i -lt 20 -and (Get-WorkerProcesses $AgentName).Count -gt 0; $i++) {
            Start-Sleep -Milliseconds 250
        }
        if ((Get-WorkerProcesses $AgentName).Count -gt 0) {
            throw "Could not stop the old $AgentName process. Close it, then launch the test bed again."
        }
    }
    Start-Hidden -Name $AgentName -ArgList $ArgList
}

function Wait-ForChatReady {
    $probe = @'
import asyncio
import json

import websockets


async def main():
    expected = {"Nexus-Manager", "Aegis-Worker", "Vigil-Worker"}
    deadline = asyncio.get_running_loop().time() + 30
    async with websockets.connect("ws://127.0.0.1:8765", open_timeout=5) as ws:
        await ws.send(json.dumps({
            "version": 1,
            "action": "register",
            "username": "user_nexus_launcher_probe",
        }))
        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                frame = json.loads(await asyncio.wait_for(ws.recv(), min(1, remaining)))
            except TimeoutError:
                continue
            if frame.get("action") != "user_list":
                continue
            users = {user["identity"]: user for user in frame.get("users", [])}
            missing = expected - users.keys()
            paused = {
                name for name in ("Aegis-Worker", "Vigil-Worker")
                if name in users and users[name].get("paused")
            }
            if not missing and not paused:
                print("Chat ready: manager, Aegis-Worker, and Vigil-Worker are registered and active.")
                return
        raise SystemExit("Chat readiness timed out. Check worker/server logs and agent pause state.")


asyncio.run(main())
'@
    $probe | & $pythonExe -
    if ($LASTEXITCODE -ne 0) { throw 'Manager and both active workers did not register in time.' }
}

try {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'src\nexus_cove') -PathType Container)) {
        throw "Repository not found at $repoRoot"
    }
    if (-not (Test-Path -LiteralPath $htmlPath -PathType Leaf)) {
        throw "Web interface not found: $htmlPath"
    }
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        throw "Project Python environment not found. Run .\.venv\Scripts\python.exe -m pip install -e `".[dev]`" first."
    }
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    Set-Location -LiteralPath $repoRoot
    Write-LaunchLog 'INFO' 'Test bed launch requested.'

    # Verify Ollama and the exact chat model before launching workers.
    try {
        $ollamaTags = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 4
    } catch {
        throw "Ollama is not responding at $ollamaUrl. Start Ollama, then launch the test bed again."
    }
    $installedModel = @($ollamaTags.models | Where-Object {
        $_.name -eq $modelName -or $_.model -eq $modelName
    })
    if ($installedModel.Count -eq 0) {
        throw "Ollama model $modelName is not installed. Run 'ollama pull $modelName', then launch again."
    }
    Write-LaunchLog 'INFO' "Ollama and model $modelName are ready."

    # 1. Server (only if the port is free)
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        Write-LaunchLog 'INFO' "Port $port already in use; reusing the running server."
    } else {
        Start-Hidden -Name 'server' -ArgList @('-m', 'nexus_cove.transport.websocket.server', '--port', "$port")
    }

    # Wait until the server is listening (up to 15 seconds)
    $ready = $false
    for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
        Start-Sleep -Milliseconds 250
        if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { $ready = $true }
    }
    if (-not $ready) { throw "Server did not start listening on port $port. See logs\server.err.log." }
    Write-LaunchLog 'INFO' "Server listening on $uri"

    # 2. Manager and workers
    # Never start a second copy of an agent: duplicates cannot register with the server.
    if (Test-AgentRunning 'nexus_cove.orchestration.manager') {
        Write-LaunchLog 'INFO' 'Manager already running; not starting another.'
    } else {
        Start-Hidden -Name 'manager' -ArgList @('-m', 'nexus_cove.orchestration.manager', '--uri', $uri)
        Start-Sleep -Seconds 2
    }
    Ensure-Worker -AgentName 'Aegis-Worker' -ArgList @('-m', 'nexus_cove.agents.worker', '--name', 'Aegis-Worker', '--test-backend', '--uri', $uri, '--model', $modelName, '--start-conversation', 'Vigil-Worker')
    Ensure-Worker -AgentName 'Vigil-Worker' -ArgList @('-m', 'nexus_cove.agents.worker', '--name', 'Vigil-Worker', '--capability', 'analysis', '--test-backend', '--uri', $uri, '--model', $modelName)

    Wait-ForChatReady

    # 3. Browser GUI
    Start-Process -FilePath $htmlPath
    Write-LaunchLog 'SUCCESS' 'Test bed launched; web\index.html opened.'
}
catch {
    Write-LaunchLog 'ERROR' $_.Exception.Message
    Start-Process -FilePath 'notepad.exe' -ArgumentList $launchLog
    exit 1
}
exit 0
