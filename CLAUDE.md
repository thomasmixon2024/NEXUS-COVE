# NEXUS COVE — Lead Systems Engineering Contract

<!-- BEGIN session-continuity (managed by install.py; edit the file in the patch, not here) -->
## Session Start and End (required, every session)

**Start.** A SessionStart hook runs `python3 .claude/initialize_session.py` (use `python` on Windows). Its output appears in your context under "SESSION CONTINUITY GUIDE". If that output is missing, run the command yourself once. CLAUDE.md is already loaded, so do not read it again. Open your first reply with the last task, the first next step, and the "Checkpoint vs repo" line (MATCHES, CHANGED, DIVERGED or UNKNOWN). Ask only if the checkpoint conflicts with the user's request.

**End.** When a significant task finishes, save a manual checkpoint. Write a JSON file to the OS temp directory containing `task_description` (string), `accomplishments` (list of strings) and `next_steps` (list of strings). Then run `python3 .claude/memory/save_checkpoint.py --file <that path>` (use `python` on Windows). The SessionEnd hook records git facts automatically but cannot describe your work, so the manual checkpoint is required.

**Shell setup.** The commands under "Development commands" are PowerShell syntax. Use the block for your environment.

Windows (PowerShell, repo root):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q; if ($LASTEXITCODE -ne 0) { throw "tests failed" }
python -m compileall -q src tests
```

Termux/Ubuntu (bash, repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q && python -m compileall -q src tests
```
<!-- END session-continuity -->


## Purpose
NEXUS COVE is a local multi-agent orchestration framework that runs entirely on-device (no cloud, no API keys). It coordinates AI agents through explicit domain models, a WebSocket transport layer, scheduling policies, execution backends, SQLite persistence, and real-time observability.

**Core Philosophy**: *"Zero cloud. Zero API keys. Absolute edge."* — Built to run anywhere Python runs, including Android via Termux.

## Environment

- **Shell**: Ubuntu LTS inside Termux on Android (proot-distro)
- **OS**: Linux 6.17.0-PRoot-Distro running under Termux
- **Architecture**: ARM64 (Android ARM64)
- **SD Card**: Mounted at `/sdcard` (bind mount from `/storage/emulated/0`) — **FULL READ/WRITE ACCESS** to all Android files, media, downloads, documents
- **Preflight Project**: Accessible at `/sdcard/Documents/Preflight` — a separate git repository with its own CLAUDE.md, assets, automation, data, and docs
- **Local Storage**: All data persists in `/root/` — no cloud, no API keys
- **Network**: Localhost-only — WebSocket on 127.0.0.1:8765, static HTTP on 127.0.0.1:8080
- **Git Remote**: `origin` at `git@github.com:thomasmixon2024/NEXUS-COVE.git` (fetch & push)
- **Trusted Repo**: `/root/NEXUS-COVE` local repository with remote `origin` tracking `origin/main`
- **Key Services**: Ollama (local LLM backend, loopback), WebSocket transport (ws://127.0.0.1:8765), static HTTP server (http://127.0.0.1:8080)
- **Sensitive Data**: Any file holding personal, confidential, or regulated material must be handled per the [named+specifics] bar

## Project Structure and Optimization

### Source File Summary (38 Python files in `src/nexus_cove/`)

**Largest files (performance-critical):**
- `agents/worker.py` (21KB) — Main worker execution loop, task dispatch, backend integration
- `transport/websocket/server.py` (19KB) — WebSocket server, message routing, broadcast logic
- `agents/memory.py` (12KB) — Per-agent JSONL message log with highlights and checkpoints
- `agents/tools.py` (11KB) — Tool assistants (Debug, Dev, First Principles) triggered by keywords
- `orchestration/manager.py` (10KB) — Manager WebSocket connection, task scheduling, result handling
- `storage/sqlite.py` (8KB) — SQLite persistence with migration system and VACUUM support

**Key modules by domain:**
- `core/models.py` (1.7KB) — Dataclasses: Task, TaskResult, Agent (slots=True for memory efficiency)
- `core/protocols.py` (1.7KB) — Message encoding/decoding with protocol versioning
- `core/dialogue.py` (2.6KB) — Turn-limit guard for agent replies (10/5min window)
- `core/exceptions.py` (277B) — Custom exception hierarchy (CoveError, ProtocolError, AgentUnavailable)
- `orchestration/scheduler.py` (813B) — Least-load capable agent selection
- `orchestration/task_registry.py` (1KB) — In-memory task tracking dictionary
- `orchestration/registry.py` (880B) — Agent registration and status lookup
- `observability/metrics.py` (1.2KB) — Runtime metrics snapshot (submitted/completed/failed)
- `observability/logging.py` (380B) — JSON log formatter with task_id/agent_id/event fields
- `storage/interface.py` (340B) — Storage protocol definition
- `utils/jsonl.py` (1.8KB) — Stream-oriented JSONL readers/writers with corrupt-line skipping
- `utils/reconnection.py` (974B) — Exponential backoff with jitter for WebSocket reconnection
- `agents/pause.py` (1.6KB) — Global and per-agent pause flag system
- `agents/knowledge.py` (2.3KB) — Per-agent knowledge store with SHARE prefix parsing
- `agents/personality.py` (2.3KB) — Personality TOML loader and system prompt builder
- `agents/backends/deterministic_backend.py` (1KB) — Test-only task execution backend
- `agents/backends/base.py` (277B) — AgentBackend protocol definition
- `agents/starter.py` (2.9KB) — Periodic conversation starter with model fallback
- `agents/tools.py` (11KB) — Tool assistants for different agent personalities

### Performance Optimization Opportunities

1. **SQLite Performance:**
   - Add `PRAGMA journal_mode=WAL` for better concurrent read performance
   - Set `PRAGMA synchronous=NORMAL` (reduces fsync overhead at small safety cost)
   - Configure `PRAGMA cache_size=-64` (64MB cache for frequently accessed data)
   - Call `vacuum()` after heavy write workloads to minimize database file size

2. **JSON Serialization:**
   - Consider using `orjson` or `ujson` for faster, smaller JSON serialization
   - Current `json.dumps` with `ensure_ascii=False` is adequate but not optimized
   - The `_json_default` in protocols.py could be optimized for the specific dataclass types used

3. **Agent Memory System:**
   - Message log grows indefinitely - consider automatic rotation after N entries
   - `_count()` reads entire JSONL file each time - could be cached or use seek-based counting
   - Highlights system preserves only 50 entries (MAX_HIGHLIGHTS) - verify this is optimal
   - Session journal trimmed to 50 entries (MAX_SESSION_CHECKPOINTS) - could be configurable

4. **WebSocket Broadcast:**
   - Current `_send_to_all` sends to ALL clients regardless of kind
   - Could filter by client kind to reduce unnecessary messages
   - Feed history limited to 200 entries (FEED_HISTORY_SIZE) - adequate for chat log

5. **Knowledge Store Loading:**
   - `KnowledgeStore.items()` loads ALL knowledge files into memory on init
   - For large knowledge bases, consider lazy loading or memory-mapped files
   - MAX_ITEMS_IN_PROMPT=4 and MAX_ITEM_CHARS=1500 already limit prompt size

6. **Tool Trigger Optimization:**
   - Tools use regex matching on lowercased text - generally fast but could be optimized
   - Debug Assistant and Dev Assistant triggers are keyword-based - no major bottlenecks

### File Size Reduction Opportunities

1. **Remove Redundant Code:**
   - Several `__init__.py` files are empty - verify if they're needed or can be removed
   - Remove any debug code or unnecessary comments
   - Consolidate similar utility functions

2. **JSON Optimization:**
   - Remove `indent=2` from non-debug JSON writes (memory.py uses `json.dump(data, handle, indent=2)`)
   - The `_write_json_atomic` function uses indent=2 - consider making this configurable
   - JSONL files don't need indentation - ensure `json.dumps(record, ensure_ascii=False) + "\n"` is used (already the case)

3. **Constant Consolidation:**
   - Several constants are defined in multiple files or could be consolidated
   - MAX_REPLY_CHARS=1200, MAX_REPLY_TOKENS=320 in ollama_replier.py
   - DEFAULT_MAX_AGENT_TURNS=10, DEFAULT_REOPEN_AFTER_SECONDS=300.0 in dialogue.py
   - CHECKPOINT_EVERY=100, MAX_HIGHLIGHTS=50, MAX_SESSION_CHECKPOINTS=50 in memory.py

4. **Import Optimization:**
   - Verify all imports are actually used (some files may have unused imports)
   - Consider lazy imports for optional modules (already done in worker.py with TYPE_CHECKING)

5. **Dataclass Efficiency:**
   - Most dataclasses already use `slots=True` for memory efficiency
   - Verify all public dataclasses use slots=True
   - Consider `__slots__` on classes that don't currently have it

### Simplification Opportunities

1. **Reduce Duplicate Logic:**
   - Pause logic exists in both `pause.py` (global/per-agent flags) and agent-level checks
   - Verify there's no redundant pause checking across the codebase

2. **Consolidate Configuration:**
   - Runtime configuration in `settings.json` could be harmonized with project-level config
   - Some constants are defined both in code and could come from config

3. **Test Coverage Review:**
   - 40 test files exist - verify all are necessary and not duplicative
   - Integration and e2e tests should cover genuine boundaries, not trivial cases

### Termux/Ubuntu on Android Constraints

- All processing must be efficient on ARM64 architecture
- Limited RAM means minimizing in-memory data footprints
- SD card storage is slower than internal storage - optimize database reads/writes
- No cloud API keys - all optimization must be local/offline
- Network is localhost-only - transport layer can assume loopback conditions

This repository is the canonical source of truth. Git history is the mechanism for versioning; duplicate `backup`, `final`, `phase-ready`, or `old` source trees are prohibited.

## Architecture (7 Layers)

```text
┌─────────────────────────────────────────────────────────────────┐
│                      Web/UI Client (index.html)                │
│   • Nexus Chat (group + DMs)  • Speaker (TTS per agent)        │
│   • Agent controls (pause/resume/stop)  • Chat log download    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket (Protocol v1)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              WebSocket Transport (transport/websocket/server.py)│
│   • Connection lifecycle  • Message routing (register, DM,      │
│     broadcast, control, task_assign, task_result, presence)    │
│   • Agent feed (last 200 agent→agent messages to browsers)     │
│   • Chat log persistence (logs/nexus_chat.jsonl)               │
│   • Origin allowlist (loopback + localhost:8080)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Orchestration Manager (orchestration/manager.py)  │
│   • Agent Registry (capabilities, status, load)                │
│   • Task Registry (CREATED→QUEUED→ASSIGNED→RUNNING→COMPLETED)  │
│   • CapabilityLoadScheduler (least-loaded capable agent)       │
│   • DialogueGuard (10 replies/5min per agent, human resets)    │
│   • Pause awareness (global + per-agent)                       │
│   • Stop network propagation                                   │
│   • RuntimeMetrics (submitted/completed/failed/duration)       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│    Agent Worker         │  │   SQLite Storage        │
│  (agents/worker.py)     │  │  (storage/sqlite.py)    │
│                         │  │                         │
│  • Personalities        │  │  • Tasks table          │
│  • Memory (JSONL)       │  │  • TaskResults table    │
│  • Knowledge (per-agent)│  │  • Schema migrations    │
│  • Tools (Debug, Dev,      │  │  • Summary stats        │
│    First Principles)             │  │                         │
│  • Ollama Replier       │  └─────────────────────────┘
│  • Conversation Starter │
│  • Pause/Resume/Stop    │
└─────────────────────────┘
```

Boundaries:
- `core/`: domain models, protocol messages, exceptions, dialogue guard. No network or database code.
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
python -m nexus_cove.orchestration.manager --db data/cove.db
```

Run a worker:

```powershell
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

With real AI (Ollama):

```powershell
python -m nexus_cove.agents.worker --name alice --model qwen2.5:0.5b --personality Aegis-Worker
```

## Test Bed Management

The project includes scripts for managing the full NEXUS COVE test bed (server, manager, workers, static server, browser):

**Kill all NEXUS COVE processes and free ports:**
```bash
./cove-kill.sh
```
Idempotent — safe to run when nothing is up. Kills cove-worker, cove-manager, cove-server, and any process holding port 8765 or 8080.

**Launch the full test bed:**
```bash
./cove-testbed.sh              # test backend (canned replies)
./cove-testbed.sh --model      # real Ollama chat replies (requires ollama serve running)
./cove-testbed.sh --no-browser # headless mode
```
This starts: WebSocket server (ws://127.0.0.1:8765), manager, 3 workers (Aegis-Worker, Elon-Worker, Vigil-Worker), static HTTP server (http://127.0.0.1:8080/web/index.html), and opens Chrome browser.

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
8. `python -m ruff check .` passes. If Ruff is not installed, report the check as NOT RUN, not as passed.
9. Documentation matches the implementation.
10. No status document claims functionality that is not implemented and verified.
11. Security implications were considered.
12. Remaining risks are explicitly reported.

Never use words such as `complete`, `production-ready`, or `verified` unless the evidence supports them.


## Session Continuity

The SessionStart hook loads the continuity guide automatically, showing where the last session left off and what to work on next. Run `python3 .claude/initialize_session.py` manually only if the hook output is missing.

### Hook Details

**SessionStart** (`.claude/initialize_session.py`): Loads the latest checkpoint from `.claude/memory/current_checkpoint.json` and the append-only journal `.claude/memory/session_checkpoints.jsonl`. Reports:
- Checkpoint ID, timestamp, source (auto/manual)
- Task description, accomplishments, next steps
- Files touched in the previous session
- Git state comparison: `MATCHES`, `CHANGED - N new commit(s)`, `DIVERGED`, or `UNKNOWN`

**SessionEnd** (`.claude/memory/save_checkpoint.py --auto`): Saves an auto-checkpoint capturing:
- Current git HEAD, branch, last commit, and changed files (excludes `.claude/memory/`)
- Carries forward the last manual task description and next steps
- Skips if identical to previous auto-checkpoint (no new changes)

**Manual Checkpoint**:
```bash
cat > /tmp/my_checkpoint.json << 'EOF'
{"task_description": "implemented feature X", "accomplishments": ["did A", "did B"], "next_steps": ["test C"]}
EOF
python3 .claude/memory/save_checkpoint.py --file /tmp/my_checkpoint.json
```

## Available Skills (Project-Local)

These skills are installed in `.claude/skills/` and managed by `NexusCove_Skills_Plugins_Installers_v3/04_setup_optional_skills.sh`:

- `project-context` — Load Nexus Cove project context: architecture, ADRs, common commands, key files. Use at session start or when context is lost.
- `dataviz` — Design-system-agnostic data visualization method (palette validator, mark specs, interaction rules). Use before creating any chart, graph, plot, or dashboard.
- `claude-api` — Reference for the Claude API / Anthropic SDK: model IDs, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration.
- `run` — Launch and drive this project's app to verify changes work in the real app (not just tests). Falls back to built-in patterns per project type.
- `security-review` — Complete a security review of pending changes on the current branch.
- `plugin-authoring` — Make a mod: a change to Claude's own interface or behaviour (live pane, panel, status line, toast, slash command, hook).
- `init` — Initialize a new CLAUDE.md file with codebase documentation.
- `keybindings-help` — Customize keyboard shortcuts, rebind keys, add chord bindings, or modify `~/.claude/keybindings.json`.

Also available (installed by same script):
- `fewer-permission-prompts` — Reduce repeated permission prompts with narrow allow rules for safe, read-only commands.
- `workflow-authoring` — Turn a multi-step task the user repeats into a reusable skill with a clear SKILL.md.
- `code-review` — Review code changes for correctness, safety, definition-of-done.
- `simplify` — Simplify recently changed code for reuse, clarity, efficiency