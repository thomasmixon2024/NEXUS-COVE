# Development Guide

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Verify

```bash
source .venv/bin/activate
python -m compileall -q src tests
python -m pytest tests -q
python -m ruff check .
```

Or use the test runner script:
```bash
bash run_tests.sh
```

## Run locally

Start the WebSocket server first, then a worker and manager. The default endpoint is `ws://127.0.0.1:8765`.

```bash
# Terminal 1: WebSocket server
source .venv/bin/activate
python -m nexus_cove.transport.websocket.server

# Terminal 2: Manager (with SQLite storage)
source .venv/bin/activate
python -m nexus_cove.orchestration.manager --db data/cove.db

# Terminal 3: Worker
source .venv/bin/activate
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

The worker refuses to start without `--test-backend`, because the deterministic backend is the only execution backend bundled with the project. The manager module does not submit tasks by itself; `scripts/diagnostics/check_roundtrip.py` submits one task and reports the result. Real model execution is not bundled into the core.

## Session Continuity

NEXUS COVE includes session continuity hooks for Claude Code:

- **SessionStart**: `.claude/initialize_session.py` — loads latest checkpoint from `.claude/memory/current_checkpoint.json` and the append-only journal `.claude/memory/session_checkpoints.jsonl`. Reports checkpoint ID, timestamp, source (auto/manual), task description, accomplishments, next steps, files touched, and git state comparison (`MATCHES`, `CHANGED - N new commit(s)`, `DIVERGED`, or `UNKNOWN`).
- **SessionEnd**: `.claude/memory/save_checkpoint.py --auto` — saves auto-checkpoint capturing current git HEAD, branch, last commit, and changed files (excludes `.claude/memory/`). Carries forward the last manual task description and next steps. Skips if identical to previous auto-checkpoint.
- **Manual**: `.claude/memory/save_checkpoint.py --file <file.json>` — saves a manual checkpoint with task description, accomplishments, and next steps.

### Manual Checkpoint Example
```bash
cat > /tmp/my_checkpoint.json << 'EOF'
{"task_description": "implemented feature X", "accomplishments": ["did A", "did B"], "next_steps": ["test C"]}
EOF
python3 .claude/memory/save_checkpoint.py --file /tmp/my_checkpoint.json
```

## Skills & Plugins

Run installer scripts from `NexusCove_Skills_Plugins_Installers_v3/`:

```bash
./NexusCove_Skills_Plugins_Installers_v3/02_setup_required_skills.sh
./NexusCove_Skills_Plugins_Installers_v3/03_setup_required_plugins.sh
./NexusCove_Skills_Plugins_Installers_v3/04_setup_optional_skills.sh
./NexusCove_Skills_Plugins_Installers_v3/05_setup_optional_plugins.sh
```

## Agent Memory

Each agent maintains memory in `data/memory/<agent>.jsonl`. Checkpoints every 100 messages.

```python
from nexus_cove.agents.memory import AgentMemory
memory = AgentMemory(data_dir() / "memory" / "Aegis-Worker.jsonl")
memory.create_session_checkpoint()
memory.startup_flush_with_highlight_retention()
```
