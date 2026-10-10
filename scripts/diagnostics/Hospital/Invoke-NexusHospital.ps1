#Requires -Version 7.0
# =====================================================================
# Invoke-NexusHospital.ps1
# Thin CLI entry point for the NEXUS COVE Diagnostic Hospital.
#
# Usage examples:
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -Probe
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -OutputFormat Json
#   pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -Probe -IncludeRaw
# =====================================================================
[CmdletBinding()]
param(
    [Parameter()]
    [switch]$Probe,

    [Parameter()]
    [ValidateRange(1, 1440)]
    [int]$StaleMinutes = 10,

    [Parameter()]
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,

    [Parameter()]
    [ValidateSet('Text', 'Json', 'Object')]
    [string]$OutputFormat = 'Text',

    [Parameter()]
    [switch]$IncludeRaw,

    [Parameter()]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$modulePath = Join-Path $PSScriptRoot 'NexusCove.Hospital.psd1'
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    Write-Error "Hospital module manifest not found: $modulePath"
    exit 3
}

Import-Module -Name $modulePath -Force -ErrorAction Stop

$params = @{
    Probe         = $Probe
    StaleMinutes  = $StaleMinutes
    Port          = $Port
    OutputFormat  = $OutputFormat
    IncludeRaw    = $IncludeRaw
}
if ($RepoRoot) { $params['RepoRoot'] = $RepoRoot }

$report = Invoke-NexusHospital @params

# Process exit code for CI / automation callers
$code = 3
if ($null -ne $report -and $null -ne $report.ExitCode) {
    $code = [int]$report.ExitCode
}
exit $code
