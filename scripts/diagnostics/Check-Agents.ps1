#Requires -Version 7.0
# =====================================================================
# Check-Agents.ps1  (compatibility shim)
# Legacy entry point. Delegates entirely to the Diagnostic Hospital.
#
# Prefer the new interface:
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -Probe
#
# This shim preserves the original -Probe and -StaleMinutes parameters
# so existing documentation and muscle memory continue to work.
# =====================================================================
[CmdletBinding()]
param(
    [Parameter()]
    [switch]$Probe,

    [Parameter()]
    [ValidateRange(1, 1440)]
    [int]$StaleMinutes = 10
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$hospitalEntry = Join-Path $PSScriptRoot 'Hospital\Invoke-NexusHospital.ps1'
if (-not (Test-Path -LiteralPath $hospitalEntry -PathType Leaf)) {
    Write-Error "Hospital entry point not found: $hospitalEntry"
    exit 3
}

& $hospitalEntry -Probe:$Probe -StaleMinutes $StaleMinutes -OutputFormat Text
exit $LASTEXITCODE
