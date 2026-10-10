> **Historical record.** This report describes the project at the time it was written. It is not a statement of current status. See `README.md`, `CLAUDE.md`, and the test suite for what is implemented and verified now.

# NEXUS COVE Refactor Report

## What I found

The supplied archive contained three overlapping source trees: an older implementation, a backup tree, and a `PHASE3-READY` tree. The latter was the only tree containing the evolved Manager + SQLite implementation and therefore became the functional baseline.

The baseline had several integrity problems: an invalid Python test file, a manager integration test that reported failure while exiting 0, a communication test that was an unbounded script rather than a test, simulated worker execution, random token telemetry, direct Manager-to-SQLite coupling, ad-hoc string task messages, and documentation claiming verified stability beyond what the tests could prove.

## What I changed

- Consolidated the project into one `src/nexus_cove` source tree.
- Added `CLAUDE.md` as the engineering governance contract.
- Added explicit domain models for agents, tasks, statuses, and results.
- Split orchestration into registry, scheduler, task registry, and manager responsibilities.
- Added a storage protocol and isolated SQLite implementation.
- Added a versioned structured WebSocket message protocol.
- Isolated agent execution behind a backend interface.
- Removed simulated/random token telemetry from runtime code.
- Restricted the deterministic backend to explicit test/development use.
- Added structured JSON logging and real task duration/status metrics.
- Replaced legacy tests with unit/integration/e2e pytest suites.
- Added a process-exit verification test and explicit safety exit behavior.
- Added truthful architecture, operations, roadmap, security, and audit documentation.
- Replaced the old messenger page with a protocol-compatible minimal UI.

## Why

The objective was not merely to move files. The refactor establishes enforceable architectural boundaries so transport, orchestration, storage, execution, and observability can evolve independently without recreating the original god-object and duplicate-tree problems.

## Verification

- `python -m compileall -q src tests`: PASS, exit 0.
- `PYTHONPATH=src python -m pytest -q`: PASS, 15 passed, exit 0.
- Import smoke test: PASS.
- Runtime/test source scan for random or simulated token telemetry: PASS.
- Worker without a configured production backend: expected failure, exit 1.

Ruff was not run because the execution environment does not have the `ruff` module installed. No claim of lint cleanliness is made.

## Remaining risks

- There is no production model backend yet; the core deliberately does not pretend otherwise.
- WebSocket transport has no authentication/TLS and remains localhost-only.
- SQLite writes are synchronous and appropriate for the current local prototype, not high-throughput distributed deployment.
- The former Phase 3 dashboard/API remains planned rather than implemented.
- A real model backend must supply authoritative usage telemetry before token accounting can be added.

## Recommended next step

Implement one real execution backend (Ollama is a natural local candidate) behind `AgentBackend`, including authoritative model metadata and usage reporting where the provider exposes it. Then add capability-aware scheduling based on actual backend health/availability before building the Phase 3 dashboard.
