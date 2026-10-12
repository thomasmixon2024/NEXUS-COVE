<#
.SYNOPSIS
    NEXUS-COVE Project Diagnostic & File Mapping Tool
.DESCRIPTION
    Scans the repository structure to locate correct module entry points,verifies virtual environment dependencies, and maps out the appropriate Python execution commands.
#>

$ErrorActionPreference = "SilentlyContinue"
$RootPath =$PSScriptRoot

Write-Output "==================================================="
Write-Output " NEXUS-COVE SYSTEM & FILE STRUCTURE DIAGNOSTIC"
Write-Output "==================================================="

# 1. Scan for entry points and critical files
Write-Output "`n[1] Scanning Project File Structure..."
$Targets = @(
    "server.py",
    "agent_client.py",
    "src\nexus_cove\api\server.py",
    "src\nexus_cove\agents\client.py",
    "web\index.html"
)

foreach ($Target in $Targets) {
    $FullPath = Join-Path $RootPath $Target
    if (Test-Path $FullPath) {
        Write-Output "  [FOUND]     $Target"
    } else {
        Write-Output "  [NOT FOUND] $Target"
    }
}

# 2. Check Virtual Environment & Python
Write-Output "`n[2] Checking Python & Virtual Environment..."
$VenvPython = Join-Path$RootPath ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Write-Output "  [FOUND] Virtual Environment Python (.venv)"
    $PyVersion = &$VenvPython --version 2>&1
    Write-Output "          Version: $PyVersion"
} else {
    Write-Output "  [WARNING] .venv\Scripts\python.exe not found. Falling back to system Python."
    $PyVersion = python --version 2>&1
    Write-Output "          System Python: $PyVersion"
}

# 3. Check installed packages in venv
Write-Output "`n[3] Checking Installed Dependencies..."
if (Test-Path $VenvPython) {
    $InstalledPkgs = & $VenvPython -m pip list 2>&1
    if ($InstalledPkgs -match "websockets") {
        Write-Output "  [SUCCESS] 'websockets' package is installed."
    } else {
        Write-Output "  [ALERT]   'websockets' package not detected in environment."
    }
}

Write-Output "`n==================================================="
Write-Output " DIAGNOSTIC COMPLETE. USE THE MAPPING ABOVE TO RUN."
Write-Output "==================================================="