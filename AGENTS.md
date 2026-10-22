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

## Agent Architecture (v0.2.0 "Cove Horizon")

### Worker Class (`src/nexus_cove/agents/worker.py`)

The `Worker` class is the main agent runtime. Key capabilities:

| Feature | Module | Description |
|---------|--------|-------------|
| **Personality** | `personality.py` | TOML-loaded personality: name, mentor, temperament, style, interests, opening questions, memory policy |
| **Memory** | `memory.py` | JSONL log (`data/memory/<agent>.jsonl`) with highlights extraction, checkpoints, session continuity |
| **Knowledge** | `knowledge.py` | Per-agent folder (`data/knowledge/<agent>/`); `SHARE: <title>` directive for voluntary sharing |
| **Tools** | `tools.py` | GeologyAnalyzer (Aegis - reads `reference/geology.csv`), PatternFinder (Vigil - analyzes memory) |
| **Conversation Starter** | `starter.py` | Periodic questions to peer; from model or personality openings |
| **Pause Controls** | `pause.py` | Global `data/PAUSE` + per-agent `data/paused/<agent>.flag` |
| **Backends** | `backends/` | `OllamaReplier` (loopback-only, raises `ModelUnavailable`), `DeterministicBackend` (test) |

### Worker Command-Line Arguments

```bash
cove-worker [OPTIONS]

Options:
  --name TEXT              Agent name (required)
  --uri TEXT               WebSocket URI (default: ws://127.0.0.1:8765)
  --personality TEXT       Personality name (Aegis-Worker, Vigil-Worker, Elon-Worker)
  --model TEXT             Ollama model name (e.g., qwen2.5:0.5b)
  --test-backend           Use deterministic test backend
  --start-conversation TEXT  Target agent name for conversation starter
  --start-interval INTEGER   Interval in seconds (default: 300)
  --help                   Show help
```

**Required combinations:**
- `--test-backend` OR `--model` (one is required)
- `--personality` required if using `--start-conversation`

### Personality System (`src/nexus_cove/agents/personality.py`)

Personalities are defined in TOML files under `src/nexus_cove/agents/personalities/`:

```toml
# Example: Aegis-Worker.toml
name = "Aegis-Worker"
mentor = "Thomas"
temperament = "Careful, analytical, and methodical. Prioritizes accuracy over speed."
style = "Precise, structured, and thorough. Uses geological analogies."
interests = ["geology", "mineralogy", "structural analysis"]
opening_questions = [
  "What geological forces shaped this landscape?",
  "How do mineral compositions reveal formation history?"
]
memory_policy = """
Memory Management Rules:
1. Summarize conversations into core geological insights.
2. Discard repetitive chatter.
3. Retain pivotal decisions and structural observations.
"""
```

**Bundled Personalities:**
- **Aegis-Worker** — Careful, analytical, geology-focused. Has Geology Analyzer tool.
- **Vigil-Worker** — Playful, curious, pattern-seeking. Has Pattern Finder tool.
- **Elon-Worker** — First-principles, engineering-focused.

### Agent Memory (`src/nexus_cove/agents/memory.py`)

`AgentMemory` provides:
- **JSONL storage**: `data/memory/<agent>.jsonl` — every message heard/sent
- **Highlights extraction**: Key insights auto-extracted from conversations
- **Checkpoints**: Periodic snapshots for session continuity
- **Session journal**: Human-readable summary of each session
- **Prompt injection**: Recent entries + highlights included in every model prompt

### Per-Agent Knowledge (`src/nexus_cove/agents/knowledge.py`)

- Each agent reads only its own folder: `data/knowledge/<agent>/`
- Knowledge items are plain text/markdown files
- **SHARE directive**: In a direct-message reply, an agent can write `SHARE: <title>` on its own line
  - The line is removed from the visible reply
  - The item is copied to the recipient's knowledge folder
  - Recorded in recipient's memory
- Group replies never share knowledge

### Tools (`src/nexus_cove/agents/tools.py`)

| Tool | Agent | Data Source | Description |
|------|-------|-------------|-------------|
| GeologyAnalyzer | Aegis | `reference/geology.csv` | Reports cited rows for materials named in a message |
| PatternFinder | Vigil | Agent's memory | Counts words/questions in messages the agent has heard |

**Real data only** — no synthetic or mock data in tools.

### Conversation Starter (`src/nexus_cove/agents/starter.py`)

- `--start-conversation PEER` makes a worker send PEER a question every `--start-interval` seconds (default 300)
- Questions come from the model, or from personality's `opening_questions` if model unavailable
- Paused agents send nothing
- Receiving side's dialogue guard still limits replies to 10 per 5 minutes

### Pause Controls (`src/nexus_cove/agents/pause.py`)

- **Global pause**: `data/PAUSE` file exists → all agents and manager send no DM replies
- **Per-agent pause**: `data/paused/<agent>.flag` exists → that agent ignores DMs, group messages, and starter
- Web GUI provides pause/resume buttons per agent + global
- Only human clients may send pause commands; server refuses them from agents
- Replies run in background, so pause takes effect immediately even while reply is being written

### Dialogue Guard (`src/nexus_cove/core/dialogue.py`)

`DialogueGuard` enforces:
- **10 agent→agent replies per 5 minutes** per counterpart
- **Human messages reset all** counters immediately (reopens dialogue)
- Direct messages carry `sender_kind` (human/agent/manager)
- Agents and manager always answer human messages

### Ollama Backend (`src/nexus_cove/agents/backends/ollama_replier.py`)

- **Loopback-only**: Only connects to `127.0.0.1:11434`
- **No fake text**: Failed model call raises `ModelUnavailable` — never substitutes invented text
- **1200-char limit**: Replies trimmed at sentence boundary with `_fit()` method
- **Token budget**: Longer budget for real responses

### Running Agents

**Test topology (4 terminals):**
```bash
# Terminal 1: Server
python -m nexus_cove.transport.websocket.server

# Terminal 2: Manager
python -m nexus_cove.orchestration.manager --db data/cove.db

# Terminal 3: Worker "alice" (responder)
python -m nexus_cove.agents.worker --name alice --uri ws://127.0.0.1:8765 --test-backend

# Terminal 4: Worker "bob" (initiator with personality)
python -m nexus_cove.agents.worker --name bob --uri ws://127.0.0.1:8765 --test-backend --personality Vigil-Worker --start-conversation alice --start-interval 10
```

**With real AI:**
```bash
# Replace --test-backend with --model
python -m nexus_cove.agents.worker --name alice --model qwen2.5:0.5b --personality Aegis-Worker --uri ws://127.0.0.1:8765
```

## Coding Style & Naming Conventions

This project targets Python 3.11-3.13, uses `ruff` rules `E`, `F`, `I`, `B`, and `UP`, and keeps line length at 100 characters. EditorConfig enforces UTF-8, LF endings, 4-space indentation, and 2-space indentation for YAML/TOML/JSON. `.pre-commit-config.yaml` also runs whitespace fixers, YAML/TOML validation, large-file checks, merger-conflict detection, and `compileall`.

## Testing Guidelines

`pytest` is the test harness; the repo organizes tests in `tests/unit`, `tests/integration`, and `tests/e2e`. Treat the suite as the source of truth: failing tests must exit non-zero, and real behavior is required rather than mock-only assertions.

### Test Levels

- `tests/unit/`: isolated, deterministic behavior
- `tests/integration/`: SQLite and WebSocket boundaries
- `tests/e2e/`: manager, worker, and result workflows

### Agent-Specific Tests

```
tests/unit/agents/
├── test_agent_pause.py
├── test_backend.py
├── test_knowledge.py
├── test_memory_and_tools.py
├── test_memory_behavior.py
├── test_personality.py
├── test_pause.py
└── test_starter.py
```

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

### Project-Local Skills (12)

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
| `simplify` | Simplify recently changed code for reuse, clarity, efficiency |

## Commit & Pull Request Guidelines

Recent history uses terse, imperative subjects with prefixes such as `fix:`, `refactor:`, and `docs:`. Keep change sets focused and include the validation command(s) you ran. No PR template was found under `.github`.