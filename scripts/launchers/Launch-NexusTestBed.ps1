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
$port     = 8765
$uri      = "ws://127.0.0.1:$port"
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

function Start-Hidden {
    param([string]$Name, [string[]]$ArgList)
    $out = Join-Path $logDir ("{0}.out.log" -f $Name)
    $err = Join-Path $logDir ("{0}.err.log" -f $Name)
    Start-Process -FilePath 'python' -ArgumentList (@('-u') + $ArgList) `
        -WorkingDirectory $repoRoot -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
    Write-LaunchLog 'INFO' "Started $Name (logs: $out)"
}

try {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'src\nexus_cove') -PathType Container)) {
        throw "Repository not found at $repoRoot"
    }
    if (-not (Test-Path -LiteralPath $htmlPath -PathType Leaf)) {
        throw "Web interface not found: $htmlPath"
    }
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    Set-Location -LiteralPath $repoRoot
    Write-LaunchLog 'INFO' 'Test bed launch requested.'

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
    if (Test-AgentRunning '--name Aegis-Worker') {
        Write-LaunchLog 'INFO' 'Aegis-Worker already running; not starting another.'
    } else {
        Start-Hidden -Name 'Aegis-Worker' -ArgList @('-m', 'nexus_cove.agents.worker', '--name', 'Aegis-Worker', '--test-backend', '--uri', $uri, '--model', 'qwen2.5:0.5b', '--start-conversation', 'Vigil-Worker')
    }
    if (Test-AgentRunning '--name Vigil-Worker') {
        Write-LaunchLog 'INFO' 'Vigil-Worker already running; not starting another.'
    } else {
        Start-Hidden -Name 'Vigil-Worker' -ArgList @('-m', 'nexus_cove.agents.worker', '--name', 'Vigil-Worker', '--capability', 'analysis', '--test-backend', '--uri', $uri, '--model', 'qwen2.5:0.5b')
    }

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
