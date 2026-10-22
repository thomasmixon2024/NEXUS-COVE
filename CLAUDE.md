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

**Benchmark**: Tested live on Android ARM64 via Termux with `qwen2.5:0.5b` (Q4_K_M) — **1.57 seconds latency (warm)**.

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
│  • Tools (Geology,      │  │  • Summary stats        │
│    Pattern)             │  │                         │
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