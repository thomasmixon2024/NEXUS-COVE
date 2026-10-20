<#
.SYNOPSIS
    Build .venv for NEXUS-COVE on Windows.
.DESCRIPTION
    Windows counterpart to scripts/setup/build-venv-termux.sh.
    Auto-detects Python 3.11-3.13, creates .venv, installs [dev] extras,
    verifies entry points, runs pytest.
#>
[CmdletBinding()]
param(
    [string]$Python = "",
    [switch]$SkipTests
)
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Write-Host "Repo: $RepoRoot" -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Not a NEXUS-COVE repo: pyproject.toml missing in $RepoRoot"
}

function Find-Python {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path $Explicit)) { throw "Python not found: $Explicit" }
        $v = & $Explicit -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($v -notmatch '^3\.(11|12|13)$') {
            throw "Python $v at $Explicit not in 3.11-3.13 (pyproject requires <3.14)"
        }
        return @{ Exe = $Explicit; PreArgs = @() }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @("3.13","3.12","3.11")) {
            $ver = & py "-$v" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -eq $v) { Write-Host "Found via py launcher: $v" -ForegroundColor Green; return @{ Exe = "py"; PreArgs = @("-$v") } }
        }
    }
    foreach ($cmd in @("python3.13","python3.12","python3.11")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { Write-Host "Found: $cmd" -ForegroundColor Green; return @{ Exe = $cmd; PreArgs = @() } }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($v -match '^3\.(11|12|13)$') { Write-Host "Found: python ($v)" -ForegroundColor Green; return @{ Exe = "python"; PreArgs = @() } }
        throw "python is $v — need 3.11-3.13 (pyproject requires <3.14)"
    }
    throw "No compatible Python. Install: winget install Python.Python.3.13"
}

$py = Find-Python -Explicit $Python
$Venv = Join-Path $RepoRoot ".venv"
if (Test-Path $Venv) { Write-Host "Removing existing .venv..." -ForegroundColor Yellow; Remove-Item -Recurse -Force $Venv }
Write-Host "Creating .venv..." -ForegroundColor Cyan
& $py.Exe @($py.PreArgs) -m venv $Venv
$VPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VPy)) { throw "Venv creation failed: $VPy missing" }

Write-Host "Upgrading pip/setuptools/wheel..." -ForegroundColor Cyan
& $VPy -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

Write-Host "Installing editable: $RepoRoot[dev]" -ForegroundColor Cyan
& $VPy -m pip install -e "$RepoRoot[dev]"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "`n-- entry points --" -ForegroundColor Cyan
$entries = @(Get-ChildItem (Join-Path $Venv "Scripts") -Filter "cove-*" -ErrorAction SilentlyContinue)
if ($entries.Count -eq 0) { throw "No cove-* entry points in $Venv\Scripts" }
$entries | ForEach-Object { Write-Host "  $($_.Name)" }

Write-Host "`n-- import smoke --" -ForegroundColor Cyan
& $VPy -c "import nexus_cove; print('nexus_cove OK')"
if ($LASTEXITCODE -ne 0) { throw "import failed" }

if (-not $SkipTests) {
    Write-Host "`n-- pytest --" -ForegroundColor Cyan
    & $VPy -m pytest -q
    if ($LASTEXITCODE -ne 0) { Write-Warning "Tests failed, but .venv is usable." }
}

Write-Host "`n.venv ready at $Venv" -ForegroundColor Green
Write-Host "Activate:   .venv\Scripts\Activate.ps1"
Write-Host "Run server: .venv\Scripts\cove-server.exe --host 127.0.0.1 --port 8765"
