# Source Inventory and Baseline Decision

Audit performed before implementation against the supplied NEXUS COVE archive.

## Observed source trees

- `The_n3xVs-Cove`: older/minimal implementation.
- `The_n3xVs-Cove'backup'`: duplicate/backup tree.
- `The_n3xVs-Cove'PHASE3-READY'`: only tree containing the evolved Manager + SQLite storage + worker client + tests.

## Baseline decision

`The_n3xVs-Cove'PHASE3-READY'` is the functional baseline for the refactor. The older trees are not treated as independent source-of-truth branches.

## Verified audit findings

- `scripts/test_workspace.py` is syntactically invalid Python.
- `test_manager_integration.py` catches its own failure and exits 0.
- `test_manager_comm.py` is an unbounded external integration script rather than a pytest test.
- `agent_client.py` fabricates token usage with `random.randint`.
- Task work is simulated with `asyncio.sleep`.
- SQLite storage itself has useful tested behavior but is coupled directly to the manager.
- Phase 3 dashboard/API is planned in documentation but not implemented.
- Multiple files are byte-for-byte duplicated across source trees.

## Refactor acceptance

Only verified, useful behavior was migrated. Generated logs, caches, backup files, conversation snapshots, and duplicate source trees were intentionally excluded from the canonical repository.
