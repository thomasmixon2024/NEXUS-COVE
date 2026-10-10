#Requires -Version 7.0
function New-NexusHealthReport {
    <#
    .SYNOPSIS
        Aggregates collector results into a single triage report.
    .DESCRIPTION
        Applies severity rules and produces both a structured object
        and a human-readable summary. Determines overall exit code.
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [object[]]$Processes,

        [Parameter(Mandatory)]
        [object]$PortHealth,

        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [object[]]$LogTriage,

        [Parameter()]
        [AllowEmptyCollection()]
        [object[]]$AgentProbes = @(),

        [Parameter()]
        [string]$RepoRoot = '',

        [Parameter()]
        [switch]$IncludeRaw
    )

    $issues = [System.Collections.Generic.List[string]]::new()
    $fixes  = [System.Collections.Generic.List[string]]::new()
    $severityScore = 0   # 0 = Healthy, 1 = Degraded, 2 = Critical

    # --- Port ---
    if ($PortHealth.Status -eq 'Critical') {
        $severityScore = [math]::Max($severityScore, 2)
        $issues.Add("WebSocket port $($PortHealth.Port) is not listening or not reachable.")
        $fixes.Add('Start the server: python -m nexus_cove.transport.websocket.server --port 8765')
    }
    elseif ($PortHealth.Status -eq 'Degraded') {
        $severityScore = [math]::Max($severityScore, 1)
        $issues.Add("Port $($PortHealth.Port) is listening but TCP connect failed.")
    }

    # --- Processes ---
    $servers  = @($Processes | Where-Object Role -eq 'server')
    $managers = @($Processes | Where-Object Role -eq 'manager')
    $workers  = @($Processes | Where-Object Role -eq 'worker')

    if ($servers.Count -eq 0) {
        $severityScore = [math]::Max($severityScore, 2)
        $issues.Add('No server process detected.')
        $fixes.Add('Start the server process.')
    }
    elseif ($servers.Count -gt 1) {
        $severityScore = [math]::Max($severityScore, 1)
        $issues.Add("Multiple server processes detected ($($servers.Count)).")
        $fixes.Add('Stop duplicate servers; keep only one listener on the port.')
    }

    if ($managers.Count -eq 0) {
        $severityScore = [math]::Max($severityScore, 1)
        $issues.Add('No manager process detected.')
        $fixes.Add('Start the manager: python -m nexus_cove.orchestration.manager')
    }

    $expectedWorkers = @('Aegis-Worker', 'Vigil-Worker')
    foreach ($name in $expectedWorkers) {
        $found = @($workers | Where-Object { $_.WorkerName -eq $name })
        if ($found.Count -eq 0) {
            $severityScore = [math]::Max($severityScore, 1)
            $issues.Add("Worker '$name' is not running.")
            $fixes.Add("Start worker: python -m nexus_cove.agents.worker --name $name --test-backend")
        }
        elseif ($found.Count -gt 1) {
            $severityScore = [math]::Max($severityScore, 1)
            $issues.Add("Duplicate instances of worker '$name' ($($found.Count)).")
            $fixes.Add("Terminate extra instances of $name.")
        }
    }

    # --- Logs ---
    foreach ($log in $LogTriage) {
        if ($log.Status -eq 'Critical' -and $log.LogName -eq '(logs directory)') {
            $severityScore = [math]::Max($severityScore, 1)
            $issues.Add('logs/ directory is missing.')
        }
        if ($log.ErrorCount -gt 0) {
            $severityScore = [math]::Max($severityScore, 1)
            $issues.Add("$($log.LogName) contains $($log.ErrorCount) recent error signature(s).")
        }
    }

    # --- Probes ---
    foreach ($probe in $AgentProbes) {
        if ($probe.Status -eq 'Critical') {
            $severityScore = [math]::Max($severityScore, 2)
            $issues.Add("Probe of $($probe.WorkerName) failed critically: $($probe.Error)")
        }
        elseif ($probe.Status -eq 'Degraded') {
            $severityScore = [math]::Max($severityScore, 1)
            $issues.Add("Probe of $($probe.WorkerName) timed out or returned no reply.")
            $fixes.Add("Verify $($probe.WorkerName) is registered and not paused.")
        }
    }

    $overall = switch ($severityScore) {
        0 { 'Healthy' }
        1 { 'Degraded' }
        2 { 'Critical' }
        default { 'Unknown' }
    }

    $exitCode = $severityScore   # 0 / 1 / 2

    $report = [pscustomobject]@{
        PSTypeName       = 'NexusCove.Hospital.HealthReport'
        TimestampUtc     = [datetime]::UtcNow.ToString('o')
        RepoRoot         = $RepoRoot
        OverallStatus    = $overall
        SeverityScore    = $severityScore
        ExitCode         = $exitCode
        IssueCount       = $issues.Count
        Issues           = @($issues)
        SuggestedFixes   = @($fixes | Select-Object -Unique)
        ProcessCount     = $Processes.Count
        ServerCount      = $servers.Count
        ManagerCount     = $managers.Count
        WorkerCount      = $workers.Count
        PortStatus       = $PortHealth.Status
        PortListening    = $PortHealth.Listening
        ProbeResults     = @($AgentProbes | Select-Object WorkerName, Status, DurationMs, Success)
    }

    if ($IncludeRaw) {
        $report | Add-Member -NotePropertyName 'RawProcesses' -NotePropertyValue $Processes
        $report | Add-Member -NotePropertyName 'RawPortHealth' -NotePropertyValue $PortHealth
        $report | Add-Member -NotePropertyName 'RawLogTriage' -NotePropertyValue $LogTriage
        $report | Add-Member -NotePropertyName 'RawAgentProbes' -NotePropertyValue $AgentProbes
    }

    $report
}
