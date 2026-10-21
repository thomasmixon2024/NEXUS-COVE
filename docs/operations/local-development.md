# Local Development

Cove binds to `127.0.0.1` by default. Do not expose it to a LAN until authentication and TLS are implemented.

## Security Model

- **Loopback only**: WebSocket server binds to `127.0.0.1:8765` (configurable via `--host`/`--port`)
- **No authentication**: Any local process can connect — intended for single-user local development
- **Origin policy**: Browser clients allowed from `null` (file://) and loopback origins only
- **Control commands**: Only browser clients (`html_client` kind) can send `control` (pause/resume/stop)

## Current Architecture (Implemented)

```
Client / UI (web/index.html)
    |
    v
WebSocket Transport (ws://127.0.0.1:8765)
    |
    v
Orchestration Manager → Scheduler/Router → Agent Registry
    |                                  |
    |                                  v
    |                            Agent Backend (deterministic / Ollama)
    v
Task/Result domain models
    |
    +--> Storage (SQLite at data/cove.db)
    +--> Observability (logs/nexus_chat.jsonl, structured JSON logging, runtime metrics)
```

## Component Boundaries (Enforced)

| Layer | Module | Responsibility |
|-------|--------|----------------|
| core | `src/nexus_cove/core/` | Domain models, protocol, exceptions — **no I/O** |
| orchestration | `src/nexus_cove/orchestration/` | Manager, scheduler, registries — **no direct SQL** |
| agents | `src/nexus_cove/agents/` | Worker lifecycle, backends — **backends replaceable** |
| transport | `src/nexus_cove/transport/websocket/` | WebSocket server, connection handling — **no scheduling logic** |
| storage | `src/nexus_cove/storage/` | Persistence interface + SQLite impl — **no transport logic** |
| observability | `src/nexus_cove/observability/` | Structured logging, chat log, metrics — **no domain logic** |
| config | `src/nexus_cove/config/` | Validated runtime configuration (reserved) |
| api | `src/nexus_cove/api/` | Future HTTP/read-only API surface |

## Running Components

### Prerequisites
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Terminal 1: WebSocket Server
```bash
python -m nexus_cove.transport.websocket.server
# Listens on ws://127.0.0.1:8765
```

### Terminal 2: Manager
```bash
python -m nexus_cove.orchestration.manager --db data/cove.db
# Connects to WebSocket, initializes SQLite storage
```

### Terminal 3: Worker
```bash
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
# Registers with manager, processes assigned tasks
```

### With Ollama (optional)
```bash
ollama pull qwen2.5:0.5b
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend --model qwen2.5:0.5b
```

### Browser GUI

**Recommended** — use the testbed launcher which starts the static server and opens the dashboard:
```bash
./cove-testbed.sh    # starts stack + opens http://127.0.0.1:8080
```

**Manual** — serve the web directory and open the URL:
```bash
cd web && python -m http.server 8080
# Then open http://127.0.0.1:8080 in your browser
```

**Legacy** — open `file://` directly (still works):
```bash
# Windows:
Start-Process .\web\index.html
# Linux/macOS/Termux:
xdg-open web/index.html  # or open, or just double-click
```

Note: The WebSocket origin check now allows both `null` (file://) and loopback HTTP origins (`http://127.0.0.1:8080`), so both methods work.

## Data Locations

| Data | Path | Notes |
|------|------|-------|
| Manager SQLite | `data/cove.db` | Override with `--db` |
| Chat log | `logs/nexus_chat.jsonl` | JSONL, append-only |
| Agent memory | `data/memory/<agent>.jsonl` | Per-agent, JSONL |
| Pause state | `data/PAUSE` (global), `data/paused/<agent>.flag` | File-based |
| Config | `NEXUS_COVE_DATA_DIR`, `NEXUS_COVE_LOG_DIR` | Env var overrides |

## Session Continuity (Claude Code)

Automatic hooks in `.claude/`:
- **SessionStart**: `.claude/initialize_session.py` → loads latest checkpoint from `.claude/memory/current_checkpoint.json` and the append-only journal `.claude/memory/session_checkpoints.jsonl`. Reports checkpoint ID, timestamp, source (auto/manual), task description, accomplishments, next steps, files touched, and git state comparison (`MATCHES`, `CHANGED - N new commit(s)`, `DIVERGED`, or `UNKNOWN`).
- **SessionEnd**: `.claude/memory/save_checkpoint.py --auto` → saves auto-checkpoint capturing current git HEAD, branch, last commit, and changed files (excludes `.claude/memory/`). Carries forward the last manual task description and next steps. Skips if identical to previous auto-checkpoint.
- **Manual**: `python3 .claude/memory/save_checkpoint.py --file <file.json>` — saves a manual checkpoint with task description, accomplishments, and next steps.

### Manual Checkpoint Example
```bash
cat > /tmp/my_checkpoint.json << 'EOF'
{"task_description": "implemented feature X", "accomplishments": ["did A", "did B"], "next_steps": ["test C"]}
EOF
python3 .claude/memory/save_checkpoint.py --file /tmp/my_checkpoint.json
```

## Skills & Plugins

Install from `NexusCove_Skills_Plugins_Installers_v3/`:
```bash
./NexusCove_Skills_Plugins_Installers_v3/02_setup_required_skills.sh
./NexusCove_Skills_Plugins_Installers_v3/03_setup_required_plugins.sh
./NexusCove_Skills_Plugins_Installers_v3/04_setup_optional_skills.sh
./NexusCove_Skills_Plugins_Installers_v3/05_setup_optional_plugins.sh
```

## Verification

```bash
bash run_tests.sh
# Or manually:
source .venv/bin/activate
python -m pytest tests -q
python -m ruff check .
python -m compileall -q src tests
```

## Known Limitations

- **No authentication/TLS** — do not expose beyond loopback
- **No production execution backend** — only deterministic test backend bundled
- **Ollama required for model chat** — but not for deterministic task execution
- **Single-manager architecture** — no HA or clustering
- **Chat log grows unbounded** — add rotation for long-running use (see ADR-0004)
- **Test backend vs model backend** — Workers launched with `--test-backend` only will acknowledge messages with canned "X heard you" replies but won't converse. For conversational replies, also pass `--model qwen2.5:0.5b` (or another Ollama model). The `cove-testbed.sh` script includes both flags.
