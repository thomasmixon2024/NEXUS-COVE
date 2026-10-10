# =====================================================================
# Update-TestBedShortcut.ps1
# Creates or overwrites the desktop shortcut "NEXUS_COVE_Test_Bed.lnk".
# The shortcut starts Launch-NexusTestBed.ps1 from this repository
# with -NoProfile, so the user's PowerShell profile is not loaded.
#
# Run with:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\launchers\Update-TestBedShortcut.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'

$repoRoot  = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$launcher  = Join-Path $repoRoot 'scripts\launchers\Launch-NexusTestBed.ps1'
$shortcut  = Join-Path ([Environment]::GetFolderPath('Desktop')) 'NEXUS_COVE_Test_Bed.lnk'
$psExe     = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Write-Status {
    param([string]$Tag, [string]$Message, [ConsoleColor]$Color)
    Write-Host ('[{0}] {1}' -f $Tag, $Message) -ForegroundColor $Color
}

try {
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Launcher not found: $launcher" }
    if (-not (Test-Path -LiteralPath $psExe -PathType Leaf)) { throw "Windows PowerShell not found: $psExe" }

    $link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
    $link.TargetPath       = $psExe
    $link.Arguments        = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`""
    $link.WorkingDirectory = $repoRoot
    $link.Description      = 'Launch the NEXUS COVE test bed and open the chat GUI'
    $link.IconLocation     = 'shell32.dll,220'
    $link.Save()

    # Read back to confirm what was written.
    $check = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
    if ($check.Arguments -notlike '*-NoProfile*' -or $check.Arguments -notlike '*-WindowStyle Hidden*' -or $check.Arguments -notlike "*$launcher*") {
        throw 'Shortcut read-back does not match the expected arguments.'
    }
    Write-Status 'SUCCESS' "Shortcut updated: $shortcut" Green
    Write-Host "  Arguments: $($check.Arguments)" -ForegroundColor Magenta
    exit 0
}
catch {
    Write-Status 'FAILURE' $_.Exception.Message Red
    exit 1
}
