# =====================================================================
# Run-PythonTests.ps1
# Runs the pytest suite from the repository root and exits with
# pytest's exit code. The tests start their own in-process servers,
# so no external server is needed.
#
# Run with:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\maintenance\Run-PythonTests.ps1
# =====================================================================
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $repoRoot

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'tests') -PathType Container)) {
    Write-Host '[FAILURE] tests folder not found under the repository root.' -ForegroundColor Red
    exit 1
}

Write-Host '=====================================================' -ForegroundColor Cyan
Write-Host ' RUNNING PYTEST' -ForegroundColor Cyan
Write-Host '=====================================================' -ForegroundColor Cyan
& python -m pytest tests -q
$exit = $LASTEXITCODE

Write-Host ''
if ($exit -eq 0) {
    Write-Host '[SUCCESS] All tests passed.' -ForegroundColor Green
} else {
    Write-Host ('[FAILURE] pytest exited with code {0}.' -f $exit) -ForegroundColor Red
    Write-Host 'Suggested next actions:' -ForegroundColor Magenta
    Write-Host '  1. Re-run with: python -m pytest tests -v' -ForegroundColor Magenta
}
exit $exit
