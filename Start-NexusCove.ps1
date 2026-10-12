<#
.SYNOPSIS
    NEXUS-COVE Automated Startup & Shortcut Creator with Custom Icon
.DESCRIPTION
    Launches the WebSocket server, spawns Aegis-Worker and Vigil-Worker using
    correct module paths, opens the web UI, and creates a desktop quickstart shortcut
    using a custom icon from the assets folder.
#>

$ErrorActionPreference = "Stop"
$RootPath =$PSScriptRoot

Write-Output "===================================================="
Write-Output "         INITIALIZING NEXUS-COVE SYSTEM            "
Write-Output "===================================================="

# 0. Automatically Create/Update Desktop Shortcut with Custom Icon
$ShortcutFile = Join-Path $HOME "Desktop\Launch NEXUS-COVE.lnk"

# Locate custom icon in the assets folder (.ico preferred, or fallback)
$CustomIcon = Get-ChildItem -Path (Join-Path $RootPath "assets") -Filter "*.ico" | Select-Object -First 1
if (-not $CustomIcon) {
    $CustomIcon = Get-ChildItem -Path (Join-Path $RootPath "assets") -Filter "*.png" | Select-Object -First 1
}

if ($CustomIcon) {
    $IconPath = $CustomIcon.FullName
} else {
    $IconPath = "shell32.dll,22"
}

if (!(Test-Path $ShortcutFile)) {
    Write-Output "[0/4] Creating Quickstart Desktop Shortcut..."
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutFile)
    $Shortcut.TargetPath = "pwsh.exe"
    $Shortcut.Arguments = '-NoExit -ExecutionPolicy Bypass -Command "cd ''$RootPath''; .\Start-NexusCove.ps1"'
    $Shortcut.WorkingDirectory = $RootPath
    $Shortcut.Description = "Launch NEXUS-COVE Server, Agents, and Web UI"
    $Shortcut.IconLocation = $IconPath
    $Shortcut.Save()
    Write-Output "      Shortcut created successfully on Desktop with icon from assets!"
}

# 1. Start the WebSocket Server
Write-Output "[1/4] Starting WebSocket Server..."
$serverArgs = "-NoExit -Command `"cd '$RootPath'; `$env:PYTHONPATH='src'; python -m nexus_cove.transport.websocket.server`""
Start-Process pwsh -ArgumentList $serverArgs

# Give the server a moment to bind to port 8765
Start-Sleep -Seconds 3

# 2. Launch Aegis-Worker (Ollama qwen2.5:0.5b)
Write-Output "[2/4] Launching Aegis-Worker..."
$aegisArgs = "-NoExit -Command `"cd '$RootPath'; `$env:PYTHONPATH='src'; python -m nexus_cove.agents.worker --name Aegis-Worker --personality Aegis-Worker --test-backend --model qwen2.5:0.5b --ollama-url http://127.0.0.1:11434`""
Start-Process pwsh -ArgumentList $aegisArgs

Start-Sleep -Seconds 2

# 3. Launch Vigil-Worker (Ollama qwen2.5:0.5b)
Write-Output "[3/4] Launching Vigil-Worker..."
$vigilArgs = "-NoExit -Command `"cd '$RootPath'; `$env:PYTHONPATH='src'; python -m nexus_cove.agents.worker --name Vigil-Worker --personality Vigil-Worker --test-backend --model qwen2.5:0.5b --ollama-url http://127.0.0.1:11434`""
Start-Process pwsh -ArgumentList $vigilArgs

Start-Sleep -Seconds 2

# 4. Open the Web UI
Write-Output "[4/4] Opening Web Interface..."
$HtmlPath = Join-Path $RootPath "web\index.html"
if (Test-Path $HtmlPath) {
    Start-Process $HtmlPath
} else {
    Write-Output "[WARNING] web\index.html not found. Opening via local web server..."
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$RootPath'; python -m http.server 8000"
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000"
}

Write-Output "===================================================="
Write-Output "      NEXUS-COVE DEPLOYED & RUNNING SUCCESSFULLY   "
Write-Output "===================================================="