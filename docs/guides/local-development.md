# Local Development Guide

*Complete workflow for developing and testing NEXUS-COVE locally*

---

## 🎯 Quick Start

```bash
# Clone and setup
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests to verify
python -m pytest -q
```

---

## 🏗️ Development Environment

### Requirements
- **Python 3.11+** (tested up to 3.13)
- **Ollama** (for real AI backend testing)
- **Git** (for version control)

### Recommended Tools
- **ruff** — Fast linting (configured in pyproject.toml)
- **pytest** — Test runner with asyncio support
- **pre-commit** — Git hooks for code quality

### IDE Setup
Configure your IDE to:
- Use the `.venv` interpreter
- Run `ruff` on save
- Run `pytest` with `asyncio_mode = auto`

---

## 🧪 Testing Workflow

### Test Levels

| Level | Path | Purpose |
|-------|------|---------|
| Unit | `tests/unit/` | Isolated, deterministic behavior |
| Integration | `tests/integration/` | Real SQLite, WebSocket, Ollama boundaries |
| E2E | `tests/e2e/` | Complete manager→worker→result workflows |

### Running Tests

```bash
# All tests (fast, quiet)
python -m pytest -q

# Verbose with coverage
python -m pytest -v --cov=nexus_cove --cov-report=term-missing

# Specific test file
python -m pytest tests/unit/agents/test_personality.py -v

# Specific test
python -m pytest tests/integration/test_websocket_transport.py::test_register_and_broadcast -v

# Only unit tests
python -m pytest tests/unit/ -q

# Only integration tests
python -m pytest tests/integration/ -q

# Only e2e tests
python -m pytest tests/e2e/ -q
```

### Test Patterns

```python
# Unit test example (tests/unit/agents/test_personality.py)
def test_personality_loads_from_toml():
    personality = Personality.load("Aegis-Worker")
    assert personality.name == "Aegis-Worker"
    assert "geology" in personality.interests

# Integration test example (tests/integration/test_websocket_transport.py)
async def test_register_and_broadcast():
    async with CoveWebSocketServer() as server:
        async with connect(server.uri) as ws:
            await ws.send(json.dumps({"v": 1, "kind": "register", "from": "test"}))
            msg = await ws.recv()
            assert json.loads(msg)["kind"] == "presence"

# E2E test example (tests/e2e/test_manager_worker.py)
async def test_manager_worker_task_flow():
    # Start server, manager, worker
    # Submit task
    # Verify result in storage
    pass
```

---

## 🏃 Running the Application Locally

### 4-Terminal Topology (Full Stack)

```bash
# Terminal 1: WebSocket Server
python -m nexus_cove.transport.websocket.server

# Terminal 2: Manager
python -m nexus_cove.orchestration.manager --db data/cove.db

# Terminal 3: Worker "alice" (responder, test backend)
python -m nexus_cove.agents.worker --name alice --uri ws://127.0.0.1:8765 --test-backend

# Terminal 4: Worker "bob" (initiator, with personality)
python -m nexus_cove.agents.worker --name bob --uri ws://127.0.0.1:8765 --test-backend --personality Vigil-Worker --start-conversation alice --start-interval 10
```

### 3-Terminal with Real AI (Ollama)

```bash
# Terminal 1: Server + Manager (background)
python -m nexus_cove.transport.websocket.server &
python -m nexus_cove.orchestration.manager --db data/cove.db

# Terminal 2: Worker with Ollama
python -m nexus_cove.agents.worker --name alice --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Aegis-Worker

# Terminal 3: Another worker
python -m nexus_cove.agents.worker --name bob --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Vigil-Worker --start-conversation alice --start-interval 30
```

### Web UI
Open `web/index.html` in browser (or serve it):
```bash
# Option 1: Direct file open
# Just open web/index.html in browser

# Option 2: Simple HTTP server (for CORS-free WebSocket)
python -m http.server 8080 -d web
# Then open http://localhost:8080
```

---

## 🔧 Development Commands

### Linting & Formatting
```bash
# Check (ruff)
python -m ruff check .

# Auto-fix (ruff)
python -m ruff check . --fix

# Format (ruff format)
python -m ruff format .
```

### Type Checking
```bash
# Basic compile check
python -m compileall -q src tests

# With mypy (if installed)
mypy src/nexus_cove
```

### Pre-commit
```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

---

## 📝 Adding New Features

### Adding a New Agent Backend

1. Create `src/nexus_cove/agents/backends/my_backend.py`:
```python
from nexus_cove.agents.backends.base import AgentBackend

class MyBackend(AgentBackend):
    async def reply(self, prompt: str, context: list) -> str:
        # Your implementation
        return "reply"
```

2. Register in `src/nexus_cove/agents/backends/__init__.py`:
```python
from .my_backend import MyBackend
__all__ = ["MyBackend", ...]
```

3. Add tests in `tests/unit/agents/test_backend.py`

### Adding a New Tool

1. Create tool in `src/nexus_cove/agents/tools.py`:
```python
class MyTool:
    def __init__(self, data_path: str):
        self.data_path = data_path
    
    def query(self, message: str) -> str:
        # Real data only
        return "result"
```

2. Wire into worker in `src/nexus_cove/agents/worker.py`:
```python
if self.name == "MyAgent":
    self.tools["my_tool"] = MyTool("data/my_data.csv")
```

3. Add tests in `tests/unit/agents/test_memory_and_tools.py`

### Adding a New Personality

1. Create `src/nexus_cove/agents/personalities/My-Worker.toml`:
```toml
name = "My-Worker"
mentor = "Thomas"
temperament = "Description..."
style = "Description..."
interests = ["topic1", "topic2"]
opening_questions = ["Question 1?", "Question 2?"]
memory_policy = """
Memory Management Rules:
1. Rule one
2. Rule two
"""
```

2. Test with:
```bash
python -m nexus_cove.agents.worker --name test --uri ws://127.0.0.1:8765 --test-backend --personality My-Worker
```

---

## 🐛 Debugging

### Enable Debug Logging
```bash
# Set log level
export NEXUS_COVE_LOG_LEVEL=DEBUG

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Debug Scenarios

| Issue | Debug Approach |
|-------|----------------|
| WebSocket connection fails | Check server logs, verify origin policy, check port 8765 |
| Agent not responding | Check pause flags (`data/PAUSE`, `data/paused/<agent>.flag`), DialogueGuard limits |
| Ollama replies fail | Verify `ollama serve` running, model pulled, loopback access |
| Task stuck in QUEUED | Check manager logs, agent registry capabilities, scheduler |
| Memory not persisting | Check `data/memory/<agent>.jsonl` permissions, JSONL format |

### Inspecting State

```bash
# View agent memory
cat data/memory/alice.jsonl | tail -20

# View chat log
cat logs/nexus_chat.jsonl | tail -20

# View SQLite database
sqlite3 data/cove.db "SELECT * FROM tasks;"
sqlite3 data/cove.db "SELECT * FROM task_results;"

# View knowledge folder
ls -la data/knowledge/alice/
```

---

## 📦 Building & Packaging

```bash
# Build wheel
python -m build

# Build sdist
python -m build --sdist

# Check package
twine check dist/*
```

---

## 🔄 Git Workflow

### Branch Naming
- `feature/<short-description>` — New features
- `fix/<short-description>` — Bug fixes
- `docs/<short-description>` — Documentation updates
- `refactor/<short-description>` — Code restructuring

### Commit Messages
Use conventional commits:
```
feat: add conversation starter to worker
fix: pause flag not respected during reply generation
docs: update architecture overview for 7-layer design
refactor: split worker message loop into handlers
```

### Pre-push Checklist
```bash
# Run before pushing
python -m pytest -q
python -m compileall -q src tests
python -m ruff check .
```

---

## 📚 Key Files Reference

### Core Domain
- `src/nexus_cove/core/models.py` — Task, TaskResult, Agent, enums
- `src/nexus_cove/core/protocols.py` — JSON encode/decode, protocol v1
- `src/nexus_cove/core/dialogue.py` — DialogueGuard (turn limits)
- `src/nexus_cove/core/exceptions.py` — CoveError, ProtocolError, AgentUnavailable

### Orchestration
- `src/nexus_cove/orchestration/manager.py` — Manager class, main entry
- `src/nexus_cove/orchestration/registry.py` — AgentRegistry
- `src/nexus_cove/orchestration/scheduler.py` — CapabilityLoadScheduler
- `src/nexus_cove/orchestration/task_registry.py` — TaskRegistry

### Agents
- `src/nexus_cove/agents/worker.py` — Worker class, main entry
- `src/nexus_cove/agents/backends/base.py` — AgentBackend protocol
- `src/nexus_cove/agents/backends/deterministic_backend.py` — Test backend
- `src/nexus_cove/agents/backends/ollama_replier.py` — Ollama HTTP client
- `src/nexus_cove/agents/personality.py` — Personality dataclass + loader
- `src/nexus_cove/agents/memory.py` — AgentMemory (JSONL + highlights + checkpoints)
- `src/nexus_cove/agents/knowledge.py` — KnowledgeStore + SHARE directive
- `src/nexus_cove/agents/tools.py` — GeologyAnalyzer, PatternFinder
- `src/nexus_cove/agents/starter.py` — ConversationStarter
- `src/nexus_cove/agents/pause.py` — Global + per-agent pause flags

### Transport
- `src/nexus_cove/transport/websocket/server.py` — CoveWebSocketServer

### Storage
- `src/nexus_cove/storage/interface.py` — Storage protocol
- `src/nexus_cove/storage/sqlite.py` — SQLiteStorage with migrations

### Observability
- `src/nexus_cove/observability/chatlog.py` — ChatLog (JSONL)
- `src/nexus_cove/observability/logging.py` — JsonFormatter
- `src/nexus_cove/observability/metrics.py` — RuntimeMetrics

### Config & Utils
- `src/nexus_cove/config/__init__.py` — (empty, reserved)
- `src/nexus_cove/utils/jsonl.py` — JSONL helpers
- `src/nexus_cove/utils/reconnection.py` — ExponentialBackoff

### Entry Points (pyproject.toml)
```toml
[project.scripts]
cove-server = "nexus_cove.transport.websocket.server:main"
cove-manager = "nexus_cove.orchestration.manager:main"
cove-worker = "nexus_cove.agents.worker:main"
```

### Personality Files
- `src/nexus_cove/agents/personalities/Aegis-Worker.toml`
- `src/nexus_cove/agents/personalities/Vigil-Worker.toml`
- `src/nexus_cove/agents/personalities/Elon-Worker.toml`

---

## 🔗 Useful Links

- [Architecture Overview](../architecture/overview.md)
- [Demo Installation Guide](../demo-installation-guide.md)
- [Termux + Ollama Setup](../../operations/termux-ollama.md)
- [Roadmap: Phase 3](../../roadmap/phase-3.md)
- [CHANGELOG](../../CHANGELOG.md)

---

*Built with ☕ and ⚡ by the NEXUS-COVE team*