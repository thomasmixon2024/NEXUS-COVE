#Requires -Version 7.0
function Invoke-NexusAgentProbe {
    <#
    .SYNOPSIS
        Live responsiveness probe against registered workers.
    .DESCRIPTION
        Shells out to the existing ask_agent.py diagnostic with strict
        timeout handling and structured result objects. Safe to call
        when the server is down (returns Critical status).
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,

        [Parameter()]
        [string[]]$WorkerNames = @('Aegis-Worker', 'Vigil-Worker'),

        [Parameter()]
        [int]$TimeoutSeconds = 45,

        [Parameter()]
        [string]$Uri = 'ws://127.0.0.1:8765'
    )

    $askScript = Join-Path $RepoRoot 'scripts\diagnostics\ask_agent.py'
    $results = [System.Collections.Generic.List[pscustomobject]]::new()

    if (-not (Test-Path -LiteralPath $askScript -PathType Leaf)) {
        foreach ($w in $WorkerNames) {
            $results.Add([pscustomobject]@{
                PSTypeName   = 'NexusCove.Hospital.AgentProbe'
                WorkerName   = $w
                Success      = $false
                Reply        = $null
                ExitCode     = 3
                DurationMs   = 0
                Status       = 'Critical'
                Error        = "Probe script missing: $askScript"
            })
        }
        return ,@($results.ToArray())
    }

    $python = Get-Command -Name python -ErrorAction SilentlyContinue
    if (-not $python) {
        foreach ($w in $WorkerNames) {
            $results.Add([pscustomobject]@{
                PSTypeName   = 'NexusCove.Hospital.AgentProbe'
                WorkerName   = $w
                Success      = $false
                Reply        = $null
                ExitCode     = 3
                DurationMs   = 0
                Status       = 'Critical'
                Error        = 'python executable not found on PATH'
            })
        }
        return ,@($results.ToArray())
    }

    foreach ($worker in $WorkerNames) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $reply = $null
        $exit = 3
        $errorMsg = $null
        $success = $false

        try {
            $argList = @(
                $askScript,
                $worker,
                'Hospital diagnostic probe: reply with one short sentence confirming you are alive.',
                '--timeout', $TimeoutSeconds.ToString()
            )
            $output = & $python.Source @argList 2>&1
            $exit = $LASTEXITCODE
            $sw.Stop()

            if ($exit -eq 0) {
                $success = $true
                $reply = ($output | Out-String).Trim()
            }
            else {
                $errorMsg = ($output | Out-String).Trim()
                if ([string]::IsNullOrWhiteSpace($errorMsg)) {
                    $errorMsg = "Probe exited with code $exit"
                }
            }
        }
        catch {
            $sw.Stop()
            $errorMsg = $_.Exception.Message
            $exit = 3
        }

        $status = if ($success) { 'Healthy' }
                  elseif ($exit -eq 1) { 'Degraded' }   # timeout / no reply
                  else { 'Critical' }

        $results.Add([pscustomobject]@{
            PSTypeName   = 'NexusCove.Hospital.AgentProbe'
            WorkerName   = $worker
            Success      = $success
            Reply        = $reply
            ExitCode     = $exit
            DurationMs   = [int]$sw.ElapsedMilliseconds
            Status       = $status
            Error        = $errorMsg
        })
    }

    ,@($results.ToArray())
}
