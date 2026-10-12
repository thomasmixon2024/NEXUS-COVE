<#
.SYNOPSIS
    Interactive port diagnostic and remediation script for NEXUS-COVE.
.DESCRIPTION
    Scans a specified port, identifies locking PIDs, displays active connections,
    and interactively walks you through termination and server restart confirmation.
#>

param(
    [Parameter(Mandatory = $false)]
    [int]$Port = 8765
)

# Set up colors/styling helpers
function Write-Header {
    param([string]$Text)
    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Yellow
    Write-Host "==================================================" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[SUCCESS] $Text" -ForegroundColor Green
}

function Write-WarningMsg {
    param([string]$Text)
    Write-Host "[WARNING] $Text" -ForegroundColor Red
}

Write-Header "NEXUS-COVE PORT DEBUGGER (Port: $Port)"

# Step 1: Scan for processes binding or connected to the port
Write-Info "Scanning network table for active connections on port $Port..."
try {
    $connections = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue)
} catch {
    $connections = @()
}

if ($connections.Count -eq 0) {
    Write-Success "Port $Port is completely clear! No conflicting processes found."
    $proceed = Read-Host "Would you like to launch 'cove-server' now? (y/n)"
    if ($proceed -eq 'y') {
        Write-Info "Launching cove-server..."
        cove-server
    }
    return
}

# Step 2: Extract PIDs and display information
$pids =$connections | Select-Object -ExpandProperty OwningProcess -Unique
Write-WarningMsg "Found conflict! Port $Port is currently tied up by Process ID(s): $($pids -join ', ')"

Write-Host "`nActive connection breakdown:" -ForegroundColor DarkGray
foreach ($conn in $connections) {
    Write-Host "  - Local: $($conn.LocalAddress):$($conn.LocalPort) | Remote: $($conn.RemoteAddress):$($conn.RemotePort) | State: $($conn.State) | PID: $($conn.OwningProcess)" -ForegroundColor Gray
}

# Step 3: Prompt for user confirmation to terminate
Write-Header "REMEDIATION PROTOCOL"
Write-Host "Options:"
Write-Host "  [Y] Forcefully terminate conflicting PIDs and clear port" -ForegroundColor Green
Write-Host "  [N] Abort debugging sequence" -ForegroundColor Red

$confirmation = Read-Host "`nDo you want to proceed with terminating process(es) $($pids -join ', ')?"

if ($confirmation -match '^[Yy]') {
    foreach ($targetPid in $pids) {
        try {
            Write-Info "Terminating Process ID: $targetPid..."
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
            Write-Success "Successfully killed PID $targetPid."
        } catch {
            Write-WarningMsg "Failed to kill PID $targetPid :$_"
        }
    }

    # Verify clearance
    Start-Sleep -Milliseconds 500
    $checkRemaining = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if (-eq$CheckRemaining) {
        Write-Success "Port $Port has been successfully freed up!"

        $restartServer = Read-Host "Would you like to start 'cove-server' now? (y/n)"
        if ($restartServer -match '^[Yy]') {
            Write-Info "Starting WebSocket server..."
            cove-server
        }
    } else {
        Write-WarningMsg "Port $Port still appears occupied. Manual inspection might be required."
    }
} else {
    Write-Info "Operation cancelled by user. Exiting debugging sequence."
}
