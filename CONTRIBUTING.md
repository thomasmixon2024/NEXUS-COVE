# Contributing to NEXUS COVE

Thank you for your interest in improving NEXUS COVE. This document defines how changes are accepted.

## Engineering contract

Read [CLAUDE.md](CLAUDE.md) before making any change. It is the authoritative engineering contract for layering, testing policy, telemetry rules, and the definition of done.

Key rules (non-negotiable):

- One canonical source tree: `src/nexus_cove/`. No parallel “backup”, “final”, or “phase-ready” trees.
- Dependency direction is inward: transport and storage depend on `core`; `core` imports neither.
- Tests are authoritative evidence. A change is not done until it has tests that exercise real behaviour and the suite passes.
- Telemetry must come from real runtime events. Never fabricate metrics or token counts.
- No `sys.path` mutation. No swallowed exceptions in production or test paths.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

On POSIX:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Required checks before a pull request

From the repository root:

```powershell
python -m compileall -q src tests
python -m ruff check .
python -m pytest tests -q
```

If you touch PowerShell scripts, also run the Diagnostic Hospital:

```powershell
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1
```

All of the above must exit 0.

## Pull request expectations

1. **Scope** — One logical change per PR. Do not mix refactors with feature work.
2. **Tests** — New behaviour requires new or updated tests at the appropriate level (`unit`, `integration`, or `e2e`).
3. **Docs** — Update README, architecture docs, or ADRs when behaviour or structure changes.
4. **Style** — Ruff must be clean. Prefer explicit types on public interfaces.
5. **No secrets** — Never commit credentials, API keys, or machine-specific paths.
6. **Localhost only** — Do not introduce network exposure, authentication bypasses, or unauthenticated remote endpoints without an accompanying security design and ADR.

## Code layout reminders

| Package | Responsibility |
|---------|----------------|
| `core/` | Domain models, protocol, exceptions. No I/O. |
| `orchestration/` | Manager, scheduler, registries. No direct SQL. |
| `agents/` | Worker lifecycle and backends. |
| `transport/` | WebSocket protocol and connections. |
| `storage/` | Persistence interfaces and SQLite. |
| `observability/` | Logging, metrics, chat log. |
| `config/` | Validated runtime configuration (currently minimal). |
| `api/` | Reserved for future HTTP/read-only surface. |

## Diagnostic tooling

The Diagnostic Hospital is the supported health surface:

```powershell
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -Probe
pwsh -NoProfile -File scripts\diagnostics\Hospital\Invoke-NexusHospital.ps1 -OutputFormat Json
```

Legacy `scripts/diagnostics/Check-Agents.ps1` is a compatibility shim and should not receive new features.

## Reporting issues

- Prefer concrete, reproducible steps.
- Include Python version, OS, and the output of the Hospital when reporting runtime failures.
- Security-sensitive reports should follow [SECURITY.md](SECURITY.md).

## License

No open-source license has been granted yet. See [LICENSE](LICENSE). Contributions are accepted under the understanding that the authors retain all rights until a license is published.
