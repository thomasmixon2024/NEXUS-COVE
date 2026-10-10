#Requires -Version 7.0
function Test-NexusPortHealth {
    <#
    .SYNOPSIS
        Tests whether the NEXUS COVE WebSocket port is listening and reachable.
    .DESCRIPTION
        Combines Get-NetTCPConnection (listener check) with a lightweight
        TCP connect probe. Returns a single structured health object.
    #>
    [CmdletBinding()]
    [OutputType([pscustomobject])]
    param(
        [Parameter()]
        [int]$Port = 8765,

        [Parameter()]
        [string]$HostName = '127.0.0.1',

        [Parameter()]
        [int]$ConnectTimeoutMs = 1500
    )

    $listening = $false
    $listenerPid = $null
    $connections = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    if ($connections.Count -gt 0) {
        $listening = $true
        $listenerPid = $connections[0].OwningProcess
    }

    $tcpReachable = $false
    $tcpError = $null
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $waited = $iar.AsyncWaitHandle.WaitOne($ConnectTimeoutMs, $false)
        if ($waited -and $client.Connected) {
            $tcpReachable = $true
        }
        else {
            $tcpError = "Connect timed out after ${ConnectTimeoutMs}ms"
        }
        $client.Close()
        $client.Dispose()
    }
    catch {
        $tcpError = $_.Exception.Message
    }

    $status = if ($listening -and $tcpReachable) { 'Healthy' }
              elseif ($listening -and -not $tcpReachable) { 'Degraded' }
              else { 'Critical' }

    [pscustomobject]@{
        PSTypeName     = 'NexusCove.Hospital.PortHealth'
        Port           = $Port
        HostName       = $HostName
        Listening      = $listening
        ListenerPid    = $listenerPid
        TcpReachable   = $tcpReachable
        TcpError       = $tcpError
        Status         = $status
        CheckedAtUtc   = [datetime]::UtcNow.ToString('o')
    }
}
