# NEXUS COVE — Diagnostic Hospital

Enterprise-grade health suite for the local multi-agent test bed.

## Purpose

Replace ad-hoc process string matching, unstructured log grepping, and
binary exit codes with a single, structured, severity-aware diagnostic
engine that is safe for both interactive use and CI.

## Entry points

```powershell
# Preferred
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -Probe
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -OutputFormat Json

# Legacy compatibility (delegates to Hospital)
pwsh -NoProfile -File scripts\diagnostics\Check-Agents.ps1
pwsh -NoProfile -File scripts\diagnostics\Check-Agents.ps1 -Probe
```

## Output formats

| Format   | Behaviour                                      |
|----------|------------------------------------------------|
| `Text`   | Human-readable colourised report (default)     |
| `Json`   | Single JSON document on the success stream     |
| `Object` | Raw `NexusCove.Hospital.HealthReport` object   |

## Exit codes

| Code | Meaning                                      |
|------|----------------------------------------------|
| 0    | Healthy                                      |
| 1    | Degraded (recoverable issues present)        |
| 2    | Critical (core components missing or down)   |
| 3    | Hospital infrastructure failure              |

## Collectors

| Collector                    | Responsibility                          |
|------------------------------|-----------------------------------------|
| `Get-NexusProcessInventory`  | CIM-based role-aware process inventory  |
| `Test-NexusPortHealth`       | Listener + TCP connect probe            |
| `Get-NexusLogTriage`         | Staleness + error signature extraction  |
| `Invoke-NexusAgentProbe`     | Live worker responsiveness (optional)   |
| `New-NexusHealthReport`      | Severity aggregation + remediation      |

## Design constraints (non-negotiable)

- `#Requires -Version 7.0`
- Advanced functions only (`[CmdletBinding()]`, comment-based help)
- Structured objects as primary output
- Read-only by default (no process start/stop)
- No COM, no WMI (CIM only), no aliases
- Deterministic severity model and exit codes

## Module layout

```
Hospital/
├── NexusCove.Hospital.psd1
├── NexusCove.Hospital.psm1
├── Invoke-NexusHospital.ps1          # CLI entry
├── Public/
│   └── Invoke-NexusHospital.ps1      # Exported function
└── Private/
    ├── Get-NexusProcessInventory.ps1
    ├── Test-NexusPortHealth.ps1
    ├── Get-NexusLogTriage.ps1
    ├── Invoke-NexusAgentProbe.ps1
    └── New-NexusHealthReport.ps1
```
