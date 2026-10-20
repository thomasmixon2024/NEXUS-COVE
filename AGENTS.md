# Repository Guidelines

## Project Structure & Module Organization

`src/nexus_cove` is organized by responsibility: `core/` holds domain models and protocol definitions, `orchestration/` manages manager scheduling and task routing, `agents/` owns worker lifecycle and execution backends, `transport/` handles WebSocket connections, `storage/` contains SQLite persistence, `observability/` logs and metrics, `config/` validates runtime config, and `api/` is reserved for future read-only HTTP surfaces. Keep cross-layer boundaries intact; do not let transport or storage code own scheduling logic. The default server binds to `127.0.0.1` and has no auth or TLS, so keep it local-only.

## Build, Test, and Development Commands

### Windows (PowerShell)

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m compileall -q src tests
python -m ruff check .
pre-commit run --all-files
```

### POSIX / Termux / Linux / macOS (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m compileall -q src tests
python -m ruff check .
pre-commit run --all-files
```

Or use the test runner:

```bash
bash run_tests.sh
```

Single-test example:

```bash
python -m pytest tests/integration/test_websocket_transport.py -q
```

Runtime entry points:

```bash
# Windows
python -m nexus_cove.transport.websocket.server
python -m nexus_cove.orchestration.manager
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend

# POSIX (with activated venv)
python -m nexus_cove.transport.websocket.server
python -m nexus_cove.orchestration.manager --db data/cove.db
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

## Coding Style & Naming Conventions

This project targets Python 3.11-3.13, uses `ruff` rules `E`, `F`, `I`, `B`, and `UP`, and keeps line length at 100 characters. EditorConfig enforces UTF-8, LF endings, 4-space indentation, and 2-space indentation for YAML/TOML/JSON. `.pre-commit-config.yaml` also runs whitespace fixers, YAML/TOML validation, large-file checks, merger-conflict detection, and `compileall`.

## Testing Guidelines

`pytest` is the test harness; the repo organizes tests in `tests/unit`, `tests/integration`, and `tests/e2e`. Treat the suite as the source of truth: failing tests must exit non-zero, and real behavior is required rather than mock-only assertions.

### Test Levels

- `tests/unit/`: isolated, deterministic behavior
- `tests/integration/`: SQLite and WebSocket boundaries
- `tests/e2e/`: manager, worker, and result workflows

## Session Continuity & Skills

NEXUS COVE includes:
- **Session continuity hooks** in `.claude/` (SessionStart/SessionEnd for Claude Code)
- **Skills/plugins installer** in `NexusCove_Skills_Plugins_Installers_v3/` (required/optional skills + superpowers plugin)
- **Project-local skills** in `.claude/skills/` (project-context, dataviz, claude-api, run, security-review, plugin-authoring, init, keybindings-help, fewer-permission-prompts, workflow-authoring, code-review, simplify)

### Session Continuity Hooks

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

### Project-Local Skills (11)

| Skill | Description |
|-------|-------------|
| `project-context` | Load Nexus Cove project context: architecture, ADRs, commands, key files |
| `dataviz` | Design-system-agnostic data visualization (palette validator, mark specs) |
| `claude-api` | Claude API/SDK reference: models, pricing, streaming, tools, MCP, caching |
| `run` | Launch and drive the project app to verify changes |
| `security-review` | Security review checklist for pending changes |
| `plugin-authoring` | Create Claude Code mods: panes, status lines, toasts, slash commands, hooks |
| `init` | Initialize a new CLAUDE.md with codebase documentation |
| `keybindings-help` | Customize keyboard shortcuts in `~/.claude/keybindings.json` |
| `fewer-permission-prompts` | Reduce repeated permission prompts with narrow allow rules |
| `workflow-authoring` | Turn repeated multi-step tasks into reusable skills |
| `code-review` | Review code changes for correctness, safety, definition-of-done |

Also available (installed by same script):
- `simplify` — Simplify recently changed code for reuse, clarity, efficiency

## Commit & Pull Request Guidelines

Recent history uses terse, imperative subjects with prefixes such as `fix:`, `refactor:`, and `docs:`. Keep change sets focused and include the validation command(s) you ran. No PR template was found under `.github`.
