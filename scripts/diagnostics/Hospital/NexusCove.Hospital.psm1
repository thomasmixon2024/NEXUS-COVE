#Requires -Version 7.0
# =====================================================================
# NexusCove.Hospital.psm1
# Enterprise diagnostic hospital for NEXUS COVE.
# Loads private collectors and exports the single public entry point.
# =====================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$private = Join-Path $PSScriptRoot 'Private'
$public  = Join-Path $PSScriptRoot 'Public'

Get-ChildItem -LiteralPath $private -Filter '*.ps1' -File -ErrorAction Stop |
    ForEach-Object { . $_.FullName }

Get-ChildItem -LiteralPath $public -Filter '*.ps1' -File -ErrorAction Stop |
    ForEach-Object { . $_.FullName }

Export-ModuleMember -Function 'Invoke-NexusHospital'
