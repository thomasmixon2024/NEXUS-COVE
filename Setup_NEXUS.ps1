# =====================================================================
# Setup_NEXUS.ps1
# Creates a desktop shortcut that starts the NEXUS-COVE server, then
# starts the server in its own window and opens the web interface.
#
# Run with:  powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup_NEXUS.ps1
# Logs: scripts\maintenance\Setup-NEXUS\Logs\ (created at run time)
# =====================================================================
$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$port        = 8765
$host_       = '127.0.0.1'
$toolDir     = Join-Path $projectRoot 'scripts\maintenance\Setup-NEXUS'
$logDir      = Join-Path $toolDir 'Logs'
$stamp       = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile     = Join-Path $logDir ('Setup_{0}.log' -f $stamp)
$htmlPath    = Join-Path $projectRoot 'web\index.html'
$shortcut    = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Start_Nexus_Cove.lnk'
$serverCmd   = "cove-server --host $host_ --port $port"
$exitCode    = 0

function Write-Log {
    param([string]$Level, [string]$Message, [ConsoleColor]$Color = 'White')
    $line = '{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line -ForegroundColor $Color
    if (Test-Path -LiteralPath $logDir -PathType Container) {
        Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    }
}

try {
    # Directory enforcement: never proceed outside the project root.
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'src\nexus_cove') -PathType Container)) {
        throw "Project root not found or incomplete: $projectRoot"
    }
    Set-Location -LiteralPath $projectRoot
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    Write-Log 'INFO' "Log: $logFile" Cyan

    if (-not (Test-Path -LiteralPath $htmlPath -PathType Leaf)) {
        throw "Web interface not found: $htmlPath"
    }

    # The server command must be installed (pip install -e .).
    $cmd = Get-Command cove-server -ErrorAction SilentlyContinue
    if (-not $cmd) { throw 'cove-server is not on PATH. Run: python -m pip install -e .' }
    Write-Log 'INFO' "Found server command: $($cmd.Source)" Green

    # Desktop shortcut: starts the server in a new window.
    $wshell = New-Object -ComObject WScript.Shell
    $link = $wshell.CreateShortcut($shortcut)
    $link.TargetPath       = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if (-not $link.TargetPath) { $link.TargetPath = 'powershell.exe' }
    $link.Arguments        = "-NoProfile -NoExit -Command `"$serverCmd`""
    $link.WorkingDirectory = $projectRoot
    $link.IconLocation     = 'shell32.dll,220'
    $link.Save()
    Write-Log 'INFO' "Desktop shortcut saved: $shortcut" Green

    # Start the server only if the port is free.
    $listening = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Log 'WARN' "Port $port is already in use; server not started." Yellow
    } else {
        Start-Process -FilePath $link.TargetPath -ArgumentList @('-NoProfile', '-NoExit', '-Command', $serverCmd) -WorkingDirectory $projectRoot
        Write-Log 'INFO' 'Server started in a new window.' Green
        Start-Sleep -Seconds 2
    }

    Start-Process -FilePath $htmlPath
    Write-Log 'INFO' 'Opened web\index.html in the default browser.' Green
}
catch {
    $exitCode = 1
    Write-Log 'ERROR' $_.Exception.Message Red
}

Write-Host ''
if ($exitCode -eq 0) {
    Write-Host '[SUCCESS] NEXUS-COVE is set up and running.' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Suggested next actions:' -ForegroundColor Magenta
    Write-Host '  1. Register a name in the browser window.' -ForegroundColor Magenta
    Write-Host '  2. Open a second browser window and register another name to test chat.' -ForegroundColor Magenta
} else {
    Write-Host '[FAILURE] Setup did not complete. See the log above.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Suggested next actions:' -ForegroundColor Magenta
    Write-Host ('  1. Read the log file: {0}' -f $logFile) -ForegroundColor Magenta
}
exit $exitCode
