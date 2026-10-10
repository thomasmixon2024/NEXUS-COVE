#Requires -Version 7.0
function Get-NexusLogTriage {
    <#
    .SYNOPSIS
        Triages NEXUS COVE log files for recent errors and staleness.
    .DESCRIPTION
        Scans known log locations under the repository logs/ directory.
        Extracts recent error signatures and flags stale agent logs.
        Returns structured triage objects; never throws on missing files.
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,

        [Parameter()]
        [int]$StaleMinutes = 10,

        [Parameter()]
        [int]$ErrorTailLines = 5
    )

    $logDir = Join-Path $RepoRoot 'logs'
    $results = [System.Collections.Generic.List[pscustomobject]]::new()

    if (-not (Test-Path -LiteralPath $logDir -PathType Container)) {
        $results.Add([pscustomobject]@{
            PSTypeName   = 'NexusCove.Hospital.LogTriage'
            LogName      = '(logs directory)'
            Path         = $logDir
            Exists       = $false
            LastWriteUtc = $null
            AgeMinutes   = $null
            IsStale      = $true
            ErrorCount   = 0
            RecentErrors = @()
            Status       = 'Critical'
            Notes        = 'logs/ directory does not exist'
        })
        return ,@($results)
    }

    $known = @(
        'server.out.log', 'server.err.log',
        'manager.out.log', 'manager.err.log',
        'Aegis-Worker.out.log', 'Aegis-Worker.err.log',
        'Vigil-Worker.out.log', 'Vigil-Worker.err.log',
        'launcher.log', 'nexus_chat.jsonl'
    )

    $errorPatterns = @('Traceback', '\[ERROR\]', 'Exception', 'CRITICAL', 'FATAL')

    foreach ($name in $known) {
        $path = Join-Path $logDir $name
        $exists = Test-Path -LiteralPath $path -PathType Leaf

        if (-not $exists) {
            $results.Add([pscustomobject]@{
                PSTypeName   = 'NexusCove.Hospital.LogTriage'
                LogName      = $name
                Path         = $path
                Exists       = $false
                LastWriteUtc = $null
                AgeMinutes   = $null
                IsStale      = $true
                ErrorCount   = 0
                RecentErrors = @()
                Status       = 'Unknown'
                Notes        = 'File not present'
            })
            continue
        }

        $item = Get-Item -LiteralPath $path
        $ageMin = [math]::Round(([datetime]::UtcNow - $item.LastWriteTimeUtc).TotalMinutes, 1)
        $isStale = $ageMin -gt $StaleMinutes

        $recentErrors = @()
        $errorCount = 0
        try {
            $content = Get-Content -LiteralPath $path -Tail 200 -ErrorAction SilentlyContinue
            if ($content) {
                $matched = $content | Select-String -Pattern ($errorPatterns -join '|') -SimpleMatch:$false
                $errorCount = @($matched).Count
                $recentErrors = @($matched | Select-Object -Last $ErrorTailLines | ForEach-Object { $_.Line.Trim() })
            }
        }
        catch {
            # Non-fatal; leave counts at zero
        }

        $status = if ($errorCount -gt 0) { 'Degraded' }
                  elseif ($isStale -and $name -notmatch 'jsonl|launcher') { 'Degraded' }
                  else { 'Healthy' }

        $results.Add([pscustomobject]@{
            PSTypeName   = 'NexusCove.Hospital.LogTriage'
            LogName      = $name
            Path         = $path
            Exists       = $true
            LastWriteUtc = $item.LastWriteTimeUtc.ToString('o')
            AgeMinutes   = $ageMin
            IsStale      = $isStale
            ErrorCount   = $errorCount
            RecentErrors = $recentErrors
            Status       = $status
            Notes        = $null
        })
    }

    ,@($results.ToArray())
}
