#Requires -Version 7.0
function Get-NexusProcessInventory {
    <#
    .SYNOPSIS
        Inventory of NEXUS COVE related Python processes.
    .DESCRIPTION
        Uses CIM to enumerate python.exe processes whose CommandLine
        contains nexus_cove markers. Returns structured objects only.
        Never throws on empty result sets.
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot
    )

    $filter = "Name='python.exe' OR Name='python3.exe' OR Name='python3.11.exe' OR Name='python3.12.exe' OR Name='python3.13.exe'"
    $candidates = @(Get-CimInstance -ClassName Win32_Process -Filter $filter -ErrorAction SilentlyContinue)

    $roles = @{
        'transport\.websocket\.server'   = 'server'
        'orchestration\.manager'         = 'manager'
        'agents\.worker'                 = 'worker'
    }

    $inventory = foreach ($proc in $candidates) {
        $cmd = $proc.CommandLine
        if ([string]::IsNullOrWhiteSpace($cmd)) { continue }
        if ($cmd -notmatch 'nexus_cove') { continue }

        $role = 'unknown'
        foreach ($pattern in $roles.Keys) {
            if ($cmd -match $pattern) {
                $role = $roles[$pattern]
                break
            }
        }

        $workerName = $null
        if ($role -eq 'worker' -and $cmd -match '--name\s+(\S+)') {
            $workerName = $Matches[1]
        }

        [pscustomobject]@{
            PSTypeName   = 'NexusCove.Hospital.Process'
            ProcessId    = [int]$proc.ProcessId
            ParentId     = [int]$proc.ParentProcessId
            Role         = $role
            WorkerName   = $workerName
            CommandLine  = $cmd
            CreationDate = $proc.CreationDate
            WorkingSetMB = [math]::Round(($proc.WorkingSetSize / 1MB), 1)
        }
    }

    # Guarantee array even when empty
    ,@($inventory)
}
