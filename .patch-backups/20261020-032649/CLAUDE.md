# NEXUS COVE — Lead Systems Engineering Contract

<!-- BEGIN session-continuity (managed by install.py; edit the file in the patch, not here) -->
## Session Start and End (required, every session)

**Start.** A SessionStart hook runs `python3 .claude/initialize_session.py`; its output appears in your context under "SESSION CONTINUITY GUIDE". If it is missing, run that command yourself. CLAUDE.md is already loaded, so do not `cat` it. Open your first reply with the last task, the first next step, and the "Checkpoint vs repo" line (MATCHES, CHANGED, DIVERGED or UNKNOWN). Ask only if the checkpoint conflicts with the user's request.

**End.** When a significant task finishes, save a manual checkpoint: write a JSON file outside the repo (for example `/tmp/checkpoint.json`) with `task_description` (string), `accomplishments` (list of strings) and `next_steps` (list of strings), then run `python3 .claude/memory/save_checkpoint.py --file /tmp/checkpoint.json`. A SessionEnd hook also records git facts automatically, but it cannot describe your work, so the manual checkpoint is required.

**Shell on Termux/Ubuntu** (the commands under "Development commands" are PowerShell):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q && python -m compileall -q src tests
```
<!-- END session-continuity -->


## Purpose
NEXUS COVE is an experimental local multi-agent orchestration framework. Its job is to coordinate tasks between agents through explicit domain models, a transport layer, scheduling policies, execution backends, persistence, and observability.

This repository is the canonical source of truth. Git history is the mechanism for versioning; duplicate `backup`, `final`, `phase-ready`, or `old` source trees are prohibited.

## Architecture

```text
Client / UI
    |
    v
Transport (WebSocket)
    |
    v
Orchestration Manager -> Scheduler/Router -> Agent Registry
    |                                  |
    |                                  v
    |                            Agent Backend
    v
Task/Result domain models
    |
    +--> Storage (SQLite)
    +--> Observability (logs/metrics/health)
```

Boundaries:
- `core/`: domain models, protocol messages, exceptions. No network or database code.
- `orchestration/`: task registry, scheduling, routing, manager lifecycle. No direct SQL.
- `agents/`: agent lifecycle and execution backends. Backends are replaceable.
- `transport/`: WebSocket protocol and connection lifecycle. No scheduling logic.
- `storage/`: persistence interfaces and SQLite implementation. No transport logic.
- `observability/`: structured logging and real runtime metrics.
- `config/`: validated runtime configuration.
- `api/`: future HTTP/read-only API surface.

## Development commands

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
python -m ruff check .
```

Run the local server:

```powershell
python -m nexus_cove.transport.websocket.server
```

Run a manager:

```powershell
python -m nexus_cove.orchestration.manager
```

Run a worker:

```powershell
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

## Coding conventions

- Python 3.11+.
- Type hints on public interfaces.
- Dataclasses for domain objects where appropriate.
- Structured JSON messages; do not encode state into ad-hoc strings.
- No global mutable application state except deliberately scoped process infrastructure.
- No `sys.path` mutation to make imports work.
- No swallowed exceptions in tests or production paths.
- No fake/random telemetry presented as real metrics.
- No hard-coded user-specific paths.
- Prefer small composable classes over god objects.
- Keep transport, orchestration, storage, and execution backends independently testable.

## Testing policy

Tests are authoritative evidence. A passing test must exercise real behavior. A test failure must produce a non-zero process exit status. Tests must not catch assertion errors and print success.

Test levels:
- `tests/unit/`: isolated deterministic behavior.
- `tests/integration/`: real component boundaries, including SQLite and WebSocket interactions.
- `tests/e2e/`: complete manager -> worker -> result workflows.

## Telemetry policy

Telemetry must originate from actual runtime events. Task duration is measured with a monotonic clock. Success/failure comes from execution results. Token counts are not reported until a real model backend provides authoritative usage data. Never fabricate token counts with random numbers.

## Definition of Done

A change is NOT done until all applicable items are true:

1. The implementation exists in the canonical source tree.
2. No duplicate implementation was introduced.
3. Public interfaces are typed and documented where non-obvious.
4. Unit tests cover new logic.
5. Integration/e2e coverage exists when a boundary or workflow changed.
6. Tests pass with a non-zero exit code on failure.
7. `python -m compileall -q src tests` passes.
8. Ruff passes when installed.
9. Documentation matches the implementation.
10. No status document claims functionality that is not implemented and verified.
11. Security implications were considered.
12. Remaining risks are explicitly reported.

Never use words such as `complete`, `production-ready`, or `verified` unless the evidence supports them.


## Session Continuity

To begin the next session focused on agent memory, simply run:
  python .claude/initialize_session.py

This will load your session continuity guide showing exactly where we left off and what to work on next.
