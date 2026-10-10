@{
    RootModule        = 'NexusCove.Hospital.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'a7c3e9f1-4b2d-4e8a-9c1f-6d5e8b0a2f34'
    Author            = 'NEXUS COVE Engineering'
    CompanyName       = 'NEXUS COVE'
    Copyright         = '(c) 2026 NEXUS COVE. All rights reserved.'
    Description       = 'Enterprise diagnostic hospital for NEXUS COVE — process, port, log, probe, and triage.'
    PowerShellVersion = '7.0'
    FunctionsToExport = @('Invoke-NexusHospital')
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
    PrivateData       = @{
        PSData = @{
            Tags         = @('NexusCove', 'Diagnostics', 'Health', 'Observability', 'Hospital')
            ProjectUri   = ''
            ReleaseNotes = 'Initial Hospital tier: process inventory, port health, log triage, agent probe, structured report.'
        }
    }
}
