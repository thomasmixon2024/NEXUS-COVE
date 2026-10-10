# =====================================================================
# Check-Agents.ps1
# Read-only diagnostic for the NEXUS COVE test bed. Reports:
#   - which server / manager / worker processes are running
#   - whether port 8765 and the local model (Ollama) respond
#   - whether the PAUSE file is silencing agents
#   - recent log activity per agent, errors, and the launcher log
# With -Probe it also sends each worker a test question and reports
# whether a reply came back.
#
# Run with:  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\diagnostics\Check-Agents.ps1
#            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\diagnostics\Check-Agents.ps1 -Probe
# =====================================================================
param(
    [switch]$Probe,
    [int]$StaleMinutes = 10
)
$ErrorActionPreference = 'Continue'

# Search upward from this script's folder for the repository (works from any folder).
$repoRoot = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'src\nexus_cove')) -and (Split-Path -Parent $repoRoot)) {
    $repoRoot = Split-Path -Parent $repoRoot
}
$logDir    = Join-Path $repoRoot 'logs'
$pauseFile = Join-Path $repoRoot 'data\PAUSE'
$askScript = Join-Path $repoRoot 'scripts\diagnostics\ask_agent.py'
$expectedWorkers = @('Aegis-Worker', 'Vigil-Worker')
$issues = New-Object System.Collections.Generic.List[string]
$fixes  = New-Object System.Collections.Generic.List[string]

function Section([string]$Title) {
    Write-Host ''
    Write-Host ('=== {0} ===' -f $Title) -ForegroundColor Cyan
}
function Ok([string]$Message)   { Write-Host ('[OK]   {0}' -f $Message) -ForegroundColor Green }
function Warn([string]$Message) { Write-Host ('[WARN] {0}' -f $Message) -ForegroundColor Yellow }
function Bad([string]$Message)  { Write-Host ('[FAIL] {0}' -f $Message) -ForegroundColor Red }
function Note([string]$Message) { Write-Host ('       {0}' -f $Message) }

Write-Host ('NEXUS COVE agent diagnostic  -  {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Write-Host ('Repository: {0}' -f $repoRoot)

# ---------------------------------------------------------------------
Section 'Processes'
$procs = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*nexus_cove*' })
$roles = @()
foreach ($p in $procs) {
    if ($p.CommandLine -match 'transport\.websocket\.server') { $role = 'server' }
    elseif ($p.CommandLine -match 'orchestration\.manager') { $role = 'manager' }
    elseif ($p.CommandLine -match '--name\s+(\S+)') { $role = 'worker ' + $Matches[1] }
    else { $role = 'other' }
    $roles += $role
    $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    $started = if ($proc) { $proc.StartTime.ToString('HH:mm:ss') } else { '?' }
    $memMb = if ($proc) { [math]::Round($proc.WorkingSet64 / 1MB) } else { 0 }
    Ok ('{0,-22} pid {1,-7} started {2}  memory {3} MB' -f $role, $p.ProcessId, $started, $memMb)
}
if ($procs.Count -eq 0) {
    Bad 'No nexus_cove python processes are running.'
    $issues.Add('No agent processes running.')
    $fixes.Add('Launch the test bed: double-click NEXUS_COVE_Test_Bed.lnk')
} else {
    if ($roles -notcontains 'server') { Bad 'Server process missing.'; $issues.Add('Server not running.'); $fixes.Add('Launch the test bed.') }
    if ($roles -notcontains 'manager') { Warn 'Manager process missing.'; $issues.Add('Manager not running.') }
    foreach ($w in $expectedWorkers) {
        if ($roles -notcontains ('worker ' + $w)) { Bad "Worker $w is not running."; $issues.Add("$w not running.") }
    }
}

$dups = @($roles | Group-Object | Where-Object { $_.Count -gt 1 })
foreach ($d in $dups) {
    Bad ('{0} is running {1} times. Duplicates cannot register, so one set is idle.' -f $d.Name, $d.Count)
    $issues.Add(('Duplicate {0}.' -f $d.Name))
    $fixes.Add('Stop all NEXUS processes (command below), then launch the test bed once.')
}

# ---------------------------------------------------------------------
Section 'Network and local model'
if (Get-NetTCPConnection -State Listen -LocalPort 8765 -ErrorAction SilentlyContinue) {
    Ok 'Server is listening on 127.0.0.1:8765.'
} else {
    Bad 'Nothing is listening on port 8765.'
    $issues.Add('Port 8765 is not listening.')
    $fixes.Add('Launch the test bed; check logs\server.err.log for the cause.')
}
try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
    $names = @($tags.models | ForEach-Object { $_.name })
    Ok ('Ollama reachable. Installed models: {0}' -f ($names -join ', '))
    if ($names -notcontains 'llama3.2:3b') {
        Bad 'llama3.2:3b is not installed.'
        $issues.Add('Model llama3.2:3b missing.')
        $fixes.Add('Run: ollama pull llama3.2:3b')
    }
    try {
        $loaded = @((Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/ps' -TimeoutSec 5).models | ForEach-Object { $_.name })
        if ($loaded.Count -gt 0) { Ok ('Model loaded in memory: {0}' -f ($loaded -join ', ')) }
        else { Note 'No model is loaded right now (it loads on the next reply; this is normal).' }
    } catch { Note 'Could not read the loaded-model list (older Ollama version).' }
} catch {
    Bad 'Ollama is not reachable on 127.0.0.1:11434.'
    $issues.Add('Ollama not running; workers cannot generate model replies.')
    $fixes.Add('Start Ollama (open the Ollama app, or run: ollama serve) and check again.')
}

# ---------------------------------------------------------------------
Section 'Pause switch'
if (Test-Path -LiteralPath $pauseFile) {
    Bad 'data\PAUSE exists: agents are silenced and will not reply.'
    $issues.Add('PAUSE file present.')
    $fixes.Add('Remove-Item data\PAUSE  (from the project root)')
} else {
    Ok 'No PAUSE file; agents may reply.'
}

# ---------------------------------------------------------------------
Section 'Agent activity from logs'
$logNames = @('server', 'manager', 'Aegis-Worker', 'Vigil-Worker')
$cutoff = (Get-Date).AddMinutes(-$StaleMinutes)
if (-not (Test-Path -LiteralPath $logDir)) {
    Bad 'logs folder not found: the test bed has never been launched from this folder.'
    $issues.Add('No logs folder.')
} else {
    foreach ($name in $logNames) {
        $errFile = Join-Path $logDir ("{0}.err.log" -f $name)
        $outFile = Join-Path $logDir ("{0}.out.log" -f $name)
        $files = @($errFile, $outFile) | Where-Object { Test-Path -LiteralPath $_ }
        if ($files.Count -eq 0) { Warn "$name : no log files."; continue }
        $lines = @()
        foreach ($f in $files) { $lines += Get-Content -LiteralPath $f -ErrorAction SilentlyContinue }
        $last = (Get-Item -LiteralPath $files[0]).LastWriteTime
        $countDm    = @($lines | Select-String -SimpleMatch 'Received direct message').Count
        $countReply = @($lines | Select-String -SimpleMatch 'Sent automated response').Count
        $countPause = @($lines | Select-String -SimpleMatch 'Paused: not replying').Count
        $countSupp  = @($lines | Select-String -SimpleMatch 'Not replying to').Count
        $countModel = @($lines | Select-String -SimpleMatch 'model_unavailable').Count + @($lines | Select-String -SimpleMatch 'Language model unavailable').Count
        $countErr   = @($lines | Select-String -Pattern 'Traceback|\[ERROR\]').Count
        Note ("{0}: last log write {1}" -f $name, $last.ToString('HH:mm:ss'))
        Note ("     direct messages received {0}, replies sent {1}, paused-silent {2}, turn-limit-silent {3}" -f $countDm, $countReply, $countPause, $countSupp)
        if ($last -lt $cutoff) {
            Warn ("{0} has been silent for more than {1} minutes." -f $name, $StaleMinutes)
            $issues.Add("$name silent.")
        }
        if ($countModel -gt 0) {
            Bad ("{0}: {1} model failure(s) logged." -f $name, $countModel)
            $issues.Add("$name model failures.")
            $fixes.Add('Check that Ollama is running and llama3.2:3b is installed.')
        }
        if ($countErr -gt 0) {
            Bad ("{0}: {1} error(s) logged. Last ones:" -f $name, $countErr)
            $lines | Select-String -Pattern 'Traceback|\[ERROR\]' | Select-Object -Last 3 | ForEach-Object { Note ("       " + $_.Line) }
            $issues.Add("$name errors.")
        }
    }
    $mgr = Join-Path $logDir 'manager.err.log'
    if (Test-Path -LiteralPath $mgr) {
        $reg = @(Get-Content -LiteralPath $mgr | Select-String -SimpleMatch 'agent registered').Count
        if ($reg -lt $expectedWorkers.Count) {
            Warn ("Manager has registered {0} agent(s); expected {1}." -f $reg, $expectedWorkers.Count)
            $issues.Add('Manager does not see all workers.')
            $fixes.Add('Restart the test bed so the manager starts after the server.')
        } else {
            Ok ("Manager has registered {0} agent(s)." -f $reg)
        }
    }
}

# ---------------------------------------------------------------------
Section 'Launcher log (last 5 lines)'
$launchLog = Join-Path $logDir 'launcher.log'
if (Test-Path -LiteralPath $launchLog) {
    Get-Content -LiteralPath $launchLog -Tail 5 | ForEach-Object { Note $_ }
} else {
    Note 'No launcher.log yet.'
}

# ---------------------------------------------------------------------
if ($Probe) {
    Section 'Live probe (sends one question to each worker)'
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Bad 'python is not on PATH; cannot run the probe.'
    } else {
        foreach ($w in $expectedWorkers) {
            $answer = & python $askScript $w 'Diagnostic check: reply with one short sentence.' --timeout 60
            if ($LASTEXITCODE -eq 0) { Ok ("{0} replied: {1}" -f $w, $answer) }
            elseif ($LASTEXITCODE -eq 1) { Bad ("{0} did not reply within 60 seconds." -f $w); $issues.Add("$w did not reply to probe.") }
            else { Bad ("{0} probe failed: {1}" -f $w, $answer); $issues.Add("$w probe error.") }
        }
    }
}

# ---------------------------------------------------------------------
Section 'Summary'
if ($issues.Count -eq 0) {
    Write-Host '[SUCCESS] No problems found. Agents appear active.' -ForegroundColor Green
} else {
    Write-Host ('[FAILURE] {0} problem(s) found:' -f $issues.Count) -ForegroundColor Red
    foreach ($i in $issues) { Write-Host ('  - {0}' -f $i) -ForegroundColor Red }
    Write-Host ''
    Write-Host 'Suggested next actions:' -ForegroundColor Magenta
    $n = 1
    foreach ($f in ($fixes | Select-Object -Unique)) { Write-Host ('  {0}. {1}' -f $n, $f) -ForegroundColor Magenta; $n++ }
}
exit ([int]($issues.Count -gt 0))
