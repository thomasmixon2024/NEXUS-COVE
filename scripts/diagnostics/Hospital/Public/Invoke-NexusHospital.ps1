#Requires -Version 7.0
function Invoke-NexusHospital {
    <#
    .SYNOPSIS
        Runs the full NEXUS COVE diagnostic hospital suite.
    .DESCRIPTION
        Collects process inventory, port health, log triage, and optional
        live agent probes. Produces a structured health report and a
        human-readable summary. Designed for both interactive use and
        CI/automation (JSON output + deterministic exit codes).

        Exit codes:
          0 = Healthy
          1 = Degraded
          2 = Critical
          3 = Infrastructure failure (module/collector error)

    .PARAMETER Probe
        When set, sends a live test question to each expected worker
        and records whether a reply arrives within the timeout.

    .PARAMETER StaleMinutes
        Minutes after which a log file is considered stale (default 10).

    .PARAMETER Port
        WebSocket port to check (default 8765).

    .PARAMETER OutputFormat
        'Text' (default) writes a human report to the host.
        'Json' emits a single JSON document to the success stream.
        'Object' returns the raw HealthReport object (for pipelines).

    .PARAMETER IncludeRaw
        Embeds the full collector payloads inside the report (useful
        for deep debugging). Increases output size.

    .PARAMETER RepoRoot
        Explicit repository root. When omitted the module walks upward
        from its own location until it finds src\nexus_cove.

    .EXAMPLE
        Invoke-NexusHospital
        Runs a read-only health check and prints a human report.

    .EXAMPLE
        Invoke-NexusHospital -Probe -OutputFormat Json
        Full live probe, machine-readable JSON on stdout.

    .EXAMPLE
        $r = Invoke-NexusHospital -OutputFormat Object
        $r.OverallStatus
        Captures the report object for further pipeline processing.

    .NOTES
        This cmdlet is intentionally read-only. It never starts, stops,
        or modifies any NEXUS COVE process.
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
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

    begin {
        $ErrorActionPreference = 'Stop'
        Set-StrictMode -Version Latest
    }

    process {
        try {
            # ----- Resolve repository root -----
            if (-not $RepoRoot) {
                $candidate = $PSScriptRoot
                # Walk up from Public/ -> Hospital/ -> diagnostics/ -> scripts/ -> root
                for ($i = 0; $i -lt 8; $i++) {
                    if (Test-Path -LiteralPath (Join-Path $candidate 'src\nexus_cove') -PathType Container) {
                        $RepoRoot = $candidate
                        break
                    }
                    $parent = Split-Path -Parent $candidate
                    if (-not $parent -or $parent -eq $candidate) { break }
                    $candidate = $parent
                }
            }

            if (-not $RepoRoot -or -not (Test-Path -LiteralPath (Join-Path $RepoRoot 'src\nexus_cove') -PathType Container)) {
                throw "Unable to locate NEXUS COVE repository root (src\nexus_cove not found)."
            }

            # ----- Collectors -----
            $processes  = Get-NexusProcessInventory -RepoRoot $RepoRoot
            $portHealth = Test-NexusPortHealth -Port $Port
            $logTriage  = Get-NexusLogTriage -RepoRoot $RepoRoot -StaleMinutes $StaleMinutes

            $probes = @()
            if ($Probe) {
                $probes = Invoke-NexusAgentProbe -RepoRoot $RepoRoot
            }

            # ----- Aggregate -----
            $report = New-NexusHealthReport `
                -Processes $processes `
                -PortHealth $portHealth `
                -LogTriage $logTriage `
                -AgentProbes $probes `
                -RepoRoot $RepoRoot `
                -IncludeRaw:$IncludeRaw

            # ----- Output -----
            switch ($OutputFormat) {
                'Json' {
                    $report | ConvertTo-Json -Depth 8 -Compress:$false
                }
                'Object' {
                    $report
                }
                default {
                    Write-HospitalTextReport -Report $report -Processes $processes -PortHealth $portHealth -LogTriage $logTriage -AgentProbes $probes
                }
            }

            # Deterministic exit for callers that inspect $LASTEXITCODE
            # (Only effective when the script is the entry point, not when
            #  imported as a module function. Callers should also inspect
            #  the returned ExitCode property.)
            if ($MyInvocation.InvocationName -eq '.' -or $MyInvocation.Line -match 'Invoke-NexusHospital') {
                # Module function cannot set process exit code reliably;
                # surface it on the object instead.
            }

            return $report
        }
        catch {
            $fail = [pscustomobject]@{
                PSTypeName    = 'NexusCove.Hospital.HealthReport'
                TimestampUtc  = [datetime]::UtcNow.ToString('o')
                OverallStatus = 'Critical'
                SeverityScore = 3
                ExitCode      = 3
                IssueCount    = 1
                Issues        = @("Hospital infrastructure failure: $($_.Exception.Message)")
                SuggestedFixes = @('Verify the module is intact and the repository layout is correct.')
            }

            if ($OutputFormat -eq 'Json') {
                $fail | ConvertTo-Json -Depth 4
            }
            elseif ($OutputFormat -eq 'Object') {
                $fail
            }
            else {
                Write-Host ''
                Write-Host '=== NEXUS COVE HOSPITAL — INFRASTRUCTURE FAILURE ===' -ForegroundColor Red
                Write-Host $_.Exception.Message -ForegroundColor Red
            }
            return $fail
        }
    }
}

function Write-HospitalTextReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object]$Report,
        [Parameter()][object[]]$Processes,
        [Parameter()][object]$PortHealth,
        [Parameter()][object[]]$LogTriage,
        [Parameter()][object[]]$AgentProbes
    )

    $statusColor = switch ($Report.OverallStatus) {
        'Healthy'  { 'Green' }
        'Degraded' { 'Yellow' }
        'Critical' { 'Red' }
        default    { 'Magenta' }
    }

    Write-Host ''
    Write-Host '================================================================' -ForegroundColor Cyan
    Write-Host '  NEXUS COVE  —  DIAGNOSTIC HOSPITAL' -ForegroundColor Cyan
    Write-Host ('  {0}' -f $Report.TimestampUtc) -ForegroundColor DarkCyan
    Write-Host '================================================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host ('  Overall Status : {0}' -f $Report.OverallStatus) -ForegroundColor $statusColor
    Write-Host ('  Severity Score : {0}' -f $Report.SeverityScore)
    Write-Host ('  Exit Code      : {0}' -f $Report.ExitCode)
    Write-Host ('  Repository     : {0}' -f $Report.RepoRoot)
    Write-Host ''

    # Processes
    Write-Host '--- Processes ---' -ForegroundColor Cyan
    if ($Processes.Count -eq 0) {
        Write-Host '  (none detected)' -ForegroundColor Yellow
    }
    else {
        foreach ($p in $Processes) {
            $label = if ($p.WorkerName) { '{0} ({1})' -f $p.Role, $p.WorkerName } else { $p.Role }
            Write-Host ('  [{0}] PID {1}  WS {2} MB  {3}' -f $label, $p.ProcessId, $p.WorkingSetMB, $p.CreationDate)
        }
    }
    Write-Host ''

    # Port
    Write-Host '--- Port Health ---' -ForegroundColor Cyan
    $pc = switch ($PortHealth.Status) { 'Healthy' { 'Green' } 'Degraded' { 'Yellow' } default { 'Red' } }
    Write-Host ('  Port {0} on {1} : {2}' -f $PortHealth.Port, $PortHealth.HostName, $PortHealth.Status) -ForegroundColor $pc
    Write-Host ('  Listening={0}  TcpReachable={1}  ListenerPid={2}' -f $PortHealth.Listening, $PortHealth.TcpReachable, $PortHealth.ListenerPid)
    if ($PortHealth.TcpError) {
        Write-Host ('  TCP error: {0}' -f $PortHealth.TcpError) -ForegroundColor Yellow
    }
    Write-Host ''

    # Logs
    Write-Host '--- Log Triage ---' -ForegroundColor Cyan
    foreach ($l in $LogTriage) {
        $lc = switch ($l.Status) { 'Healthy' { 'Green' } 'Degraded' { 'Yellow' } 'Critical' { 'Red' } default { 'DarkGray' } }
        $stale = if ($l.IsStale) { ' STALE' } else { '' }
        $err = if ($l.ErrorCount -gt 0) { "  errors=$($l.ErrorCount)" } else { '' }
        Write-Host ('  [{0}]{1}{2}  age={3}m' -f $l.LogName, $stale, $err, $l.AgeMinutes) -ForegroundColor $lc
        foreach ($e in $l.RecentErrors) {
            Write-Host ('         {0}' -f $e) -ForegroundColor DarkYellow
        }
    }
    Write-Host ''

    # Probes
    if ($AgentProbes.Count -gt 0) {
        Write-Host '--- Agent Probes ---' -ForegroundColor Cyan
        foreach ($pr in $AgentProbes) {
            $prc = switch ($pr.Status) { 'Healthy' { 'Green' } 'Degraded' { 'Yellow' } default { 'Red' } }
            Write-Host ('  {0} : {1}  ({2} ms)' -f $pr.WorkerName, $pr.Status, $pr.DurationMs) -ForegroundColor $prc
            if ($pr.Reply) {
                Write-Host ('         Reply: {0}' -f $pr.Reply) -ForegroundColor DarkGreen
            }
            if ($pr.Error) {
                Write-Host ('         Error: {0}' -f $pr.Error) -ForegroundColor DarkYellow
            }
        }
        Write-Host ''
    }

    # Issues & Fixes
    if ($Report.IssueCount -gt 0) {
        Write-Host '--- Issues ---' -ForegroundColor Red
        foreach ($i in $Report.Issues) {
            Write-Host ('  - {0}' -f $i) -ForegroundColor Red
        }
        Write-Host ''
        if ($Report.SuggestedFixes.Count -gt 0) {
            Write-Host '--- Suggested Fixes ---' -ForegroundColor Magenta
            $n = 1
            foreach ($f in $Report.SuggestedFixes) {
                Write-Host ('  {0}. {1}' -f $n, $f) -ForegroundColor Magenta
                $n++
            }
            Write-Host ''
        }
    }
    else {
        Write-Host '[SUCCESS] No problems found. System appears healthy.' -ForegroundColor Green
        Write-Host ''
    }

    Write-Host '================================================================' -ForegroundColor Cyan
}
