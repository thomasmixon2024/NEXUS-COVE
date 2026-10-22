<div align="center">
  <img src="assets/NEXUS-COVE-LOGO.jpg" alt="NEXUS-COVE Logo" width="420">

  <h1>NEXUS-COVE</h1>

  <p><strong>A local multi-agent orchestration framework.</strong><br>
  <em>Zero cloud. Zero API keys. Absolute edge.</em></p>

  [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
  [![Ollama](https://img.shields.io/badge/Backend-Ollama-black.svg)](https://ollama.com)
  [![Termux Ready](https://img.shields.io/badge/Android-Termux-green.svg)](https://termux.dev)
  [![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-yellow.svg)](LICENSE)
  [![Version: 0.2.0](https://img.shields.io/badge/Version-0.2.0%20%22Cove%20Horizon%22-orange.svg)](CHANGELOG.md)
</div>

---

## 🧠 What is this?

**NEXUS-COVE** is an asynchronous multi-agent orchestration framework that runs entirely on-device. It coordinates AI agents through explicit domain models, a WebSocket transport layer, scheduling policies, execution backends, SQLite persistence, and real-time observability.

Built for the edge. No cloud dependencies. No API keys required. Your data never leaves your machine.

**Benchmark**: Tested live on Android ARM64 via Termux with `qwen2.5:0.5b` (Q4_K_M) — **1.57 seconds latency (warm)**.

---

## ⚡ Core Features (v0.2.0 "Cove Horizon")

| Category | Features |
|----------|----------|
| **Agent Ecosystem** | 3 bundled personalities (Aegis, Vigil, Elon) loaded from TOML; per-agent memory, knowledge folders, and tools |
| **Orchestration** | Task registry (CREATED→QUEUED→ASSIGNED→RUNNING→COMPLETED), capability-load scheduler, agent registry |
| **Communication** | WebSocket protocol v1, group chat (Nexus Chat), direct messages, agent feed (last 200 messages replayed) |
| **Safety & Control** | Dialogue Guard (10 agent→agent replies/5 min, human resets), global + per-agent pause, human-only stop network |
| **Local LLM** | Ollama integration (loopback-only), `ModelUnavailable` exception (no fake text), 1200-char sentence-boundary limit |
| **Memory & Knowledge** | JSONL memory with highlights/checkpoints, per-agent knowledge folders, `SHARE:` directive for voluntary sharing |
| **Tools** | Geology Analyzer (Aegis - reads CSV), Pattern Finder (Vigil - analyzes memory) — real data only |
| **Conversation Starter** | Periodic questions to peers from model or personality openings |
| **Observability** | Structured JSONL chat log (downloadable as Markdown), runtime metrics, structured logging |
| **Speech Synthesis** | Edge Natural voices per agent, per-sentence emotion modulation (pitch/rate/volume) |
| **Mobile Ready** | Runs on Android via Termux; ARM64 optimized |
| **Web UI** | Real-time chat interface with locked input box, scrollable feed, agent controls, TTS |

---

## 🚀 Quick Start

**Repository**: [github.com/thomasmixon2024/NEXUS-COVE](https://github.com/thomasmixon2024/NEXUS-COVE)

```bash
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE
./run_demo.sh
```

> **⚠️ Paste one line at a time.** Some commands below open an interactive prompt. Pasting the whole block at once can cause leftover keystrokes to be consumed by the prompt, exiting the installer unexpectedly. Run each line, wait for it to finish, then paste the next. For a paste-safe automated run, use `./run_demo.sh --yes`.

**Expected Output:**

```text
🚀 Initializing NEXUS-COVE...
⏳ Starting Ollama in the background...
📥 Ensuring qwen2.5:0.5b model is downloaded...
📦 Installing Python dependencies...
🧠 Running the verification test...
✅ Ollama reachable
Warming up model...
✅ PASS — measured latency: 1.57s
   Reply: "Hello! You're testing Termux..."
```

📖 **[Full Demo Installation Guide](docs/guides/demo-installation-guide.md)** — comprehensive walkthrough with all flags, error recovery, troubleshooting, and pro tips.

### 🎮 Interactive Installer

The `run_demo.sh` script features an interactive TUI (Terminal User Interface) with error recovery:

```bash
# Interactive mode (default on TTY)
./run_demo.sh

# Automated with safe defaults (retry once, skip optional deps)
./run_demo.sh --yes

# CI / non-interactive mode (fail fast with log path)
./run_demo.sh --non-interactive

# Custom model
./run_demo.sh --model llama3.2

# Custom virtual environment
./run_demo.sh --venv /path/to/venv

# Skip Python dependencies (if already installed)
./run_demo.sh --skip-python-deps
```

**Correct launch (avoid the malformed `cd NEXUS-COVE ./run_demo.sh ...` pattern):**
```bash
cd NEXUS-COVE && ./run_demo.sh
# or
./run_demo.sh
```

### 📋 Command-Line Options

| Flag | Description |
|------|-------------|
| `-y`, `--yes` | Accept safe defaults, retry once, auto-skip optional deps, never install system packages |
| `--non-interactive` | Force non-interactive mode (fail fast on errors) |
| `--verbose` | Verbose output |
| `--log-dir <path>` | Log directory (default: `./logs/`) |
| `--skip-python-deps` | Skip Python dependency installation |
| `--with-dev` | Install dev extras (pytest, ruff, etc.) |
| `--no-dev` | Explicitly skip dev extras |
| `--venv <path>` | Virtual environment path (default: `.venv-termux` or `.venv`) |
| `--model <name>` | Ollama model (default: `qwen2.5:0.5b`) |
| `-h`, `--help` | Show help |

### 🎯 Interactive Error Recovery

When a step fails on a TTY, you'll see an actionable menu:

```
❌ Step failed: install_python_deps (exit 50)
📄 Log: logs/python-deps-20261020-143022.log

Options:
1. View full error log
2. Retry step
3. Install missing build prerequisites
4. Use prebuilt wheels only (--only-binary=:all:)
5. Skip optional dependencies and continue degraded
6. Abort
```

The script auto-detects failure patterns and suggests targeted fixes:
- **Rust/cargo/maturin errors** → Suggests `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Python.h missing** → Suggests `apt install python3-dev` (or distro equivalent)
- **gcc/cc/make missing** → Suggests `apt install build-essential` (or distro equivalent)
- **Network errors** → Suggests retry
- **pyproject.toml metadata failures** → Suggests wheel-only install

### 📁 Log Locations

All logs are written to `./logs/` (project-relative):
- `prerequisites-YYYYMMDD-HHMMSS.log`
- `ollama-YYYYMMDD-HHMMSS.log`
- `model-pull-YYYYMMDD-HHMMSS.log`
- `venv-YYYYMMDD-HHMMSS.log`
- `python-deps-YYYYMMDD-HHMMSS.log`
- `demo-YYYYMMDD-HHMMSS.log`

### ⚡ Idempotency

Re-running `./run_demo.sh` is safe:
- Reuses existing virtual environment (`.venv-termux` or `.venv`)
- Skips re-pulling already-present Ollama model
- Does not restart a healthy Ollama daemon
- `pip` handles idempotency automatically

---

## 🏗️ Architecture: 7-Layer Design

```
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

**Boundaries enforced**: No layer reaches around another for convenience. Core, orchestration, agents, transport, storage, and observability are independently testable.

---

## 🚀 Running the Application

`./run_demo.sh` verifies your environment and exits. To actually run NEXUS-COVE, start the testbed which launches all daemons:

### One-Command Testbed (Recommended)

```bash
# With real Ollama AI responses (qwen2.5:0.5b)
./cove-testbed.sh --model --no-browser

# With canned test replies (fast, no Ollama needed)
./cove-testbed.sh --no-browser
```

This starts:
- **WebSocket Server** (port 8765)
- **Orchestration Manager** (SQLite DB)
- **3 Agent Workers**: Aegis-Worker, Elon-Worker, Vigil-Worker
- **Static Server** (port 8080) serving `web/index.html`

Then open **http://127.0.0.1:8080/web/index.html** in your browser.

> **Note**: `cove-testbed.sh` now includes an Ollama preflight check. If Ollama isn't running, it will exit with a clear error: `❌ Ollama not running. In a Termux session run: ollama serve`

### Manual Process Launch (Advanced)

**Terminal 1 — WebSocket Server**
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-server
```
Default bind: `ws://0.0.0.0:8765`. Leave running.

**Terminal 2 — Manager**
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-manager --db data/cove.db
```
Owns the task DB and routes messages. Leave running.

**Terminal 3 — Worker "Aegis-Worker" (responder, geology tool)**
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-worker --name Aegis-Worker --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Aegis-Worker
```

**Terminal 4 — Worker "Vigil-Worker" (initiator, pattern tool)**
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-worker --name Vigil-Worker --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Vigil-Worker --start-conversation Aegis-Worker --start-interval 10
```

**Terminal 5 — Worker "Elon-Worker" (first-principles thinker)**
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-worker --name Elon-Worker --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Elon-Worker
```

### Stop Everything
```bash
./cove-kill.sh
```

### Web UI Features

Open `web/index.html` in a browser (connects to `ws://127.0.0.1:8765`):

- **Nexus Chat**: Single channel for humans + agents; agent→agent messages shown inline with `@sender to @recipient` attribution
- **Locked Input Box**: Message input stays fixed at bottom; only chat feed scrolls (proven Discord/Slack grid layout)
- **Agent Feed** (`# Agent conversations`): Read-only replay of last 200 agent→agent messages for late-joining browsers
- **Agent Controls**: Per-agent pause/resume, global pause all, Stop Network (cascades to all processes)
- **Speech Synthesis**: Speaker button reads agent messages aloud in their own Edge Natural voices with per-sentence emotion modulation
- **Chat Log**: Download full conversation as Markdown; unsaved changes warning on navigation
- **Mobile Responsive**: Sidebar collapses to slide-over drawer on mobile

---

### Real AI Replies (Ollama)

Use `--model qwen2.5:0.5b` (or any Ollama model). Workers then reply via Ollama instead of the canned backend. Requires the model (`run_demo.sh` pulls it).

> ⚠️ Without `--test-backend` or `--model`, the worker exits with `No production execution backend is configured.`

**Latency**: ~16s cold start (model load), **~1.57s warm** (measured on Android ARM64 Termux).

---

## 📱 Mobile / Termux Setup

Want to run it on Android? We wrote the whole playbook for it.

👉 [Read the Termux + Ollama Setup Guide](docs/operations/termux-ollama.md)

---

## 📂 Project Structure

```text
NEXUS-COVE/
├── assets/                      # Logo, branding
├── cove-testbed.sh              # One-command full stack launch (server + manager + 3 workers + static)
├── cove-kill.sh                 # Kills all processes, frees ports
├── run_demo.sh                  # Interactive demo installer (bash, ~866 lines)
├── examples/
│   └── agent-invocations/       # Example agent persona definitions (Architect, Debug, Docs-Ops, Validator)
├── plugins/
│   ├── nexus-cove-enhancement/  # Claude Code plugin (hooks + TypeScript types)
│   └── README.md                # Plugin directory overview
├── archive/                     # Superseded/consolidated directories
│   ├── NexusCove_Skills_Plugins_Installers_v3/  # Skill/plugin installer scripts
│   ├── pack_v3/                 # Packaged artifact (.claude/, src/)
│   ├── reference/               # Former reference data (geology.csv)
│   ├── CODE_OF_CONDUCT.md       # Archived (solo project)
│   └── SECURITY.md              # Archived (solo project)
├── docs/
│   ├── architecture/overview.md     # 7-layer architecture
│   ├── guides/
│   │   ├── demo-installation-guide.md
│   │   └── local-development.md
│   ├── operations/termux-ollama.md
│   └── roadmap/phase-3.md
├── src/nexus_cove/                 # Core framework
│   ├── core/                  # Domain models, protocols, dialogue guard
│   ├── orchestration/         # Manager, registry, scheduler, task registry
│   ├── agents/                # Worker, backends, personality, memory, knowledge, tools, starter, pause
│   │   ├── backends/          # Ollama, deterministic backends
│   │   └── personalities/     # TOML personality files
│   ├── transport/websocket/   # WebSocket server (protocol v1)
│   ├── storage/               # SQLite with migrations
│   ├── observability/         # Chat log, metrics, structured logging
│   └── utils/                 # JSONL helpers, reconnection logic
├── tests/
│   ├── unit/                  # Isolated deterministic tests
│   ├── integration/           # SQLite, WebSocket, Ollama boundaries
│   └── e2e/                   # Manager→Worker→Result workflows
├── web/index.html              # Complete chat interface with locked input, speech synthesis
├── pyproject.toml              # PEP 621 packaging
├── CHANGELOG.md                # Version history
├── CLAUDE.md                   # Project instructions for Claude Code
├── AGENTS.md                   # Agent development guidelines
└── LICENSE                     # All Rights Reserved
```

---

## 🛠️ Development Commands

From repository root:

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"

# Test
python -m pytest -q

# Lint
python -m ruff check .

# Compile check
python -m compileall -q src tests

# Run server
python -m nexus_cove.transport.websocket.server

# Run manager
python -m nexus_cove.orchestration.manager --db data/cove.db

# Run worker (test backend)
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend

# Run worker (real Ollama)
python -m nexus_cove.agents.worker --name Aegis-Worker --model qwen2.5:0.5b --personality Aegis-Worker
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
python -m ruff check .
```

---

## 🧪 Test Structure

```
tests/
├── unit/
│   ├── core/           # test_dialogue.py, test_models.py, test_protocols.py
│   ├── orchestration/  # test_manager_submit.py, test_scheduler.py, test_task_registry.py
│   ├── storage/        # test_sqlite.py
│   ├── transport/      # test_server_protocol.py
│   └── agents/         # test_agent_pause.py, test_backend.py, test_knowledge.py,
│                       # test_memory_and_tools.py, test_memory_behavior.py,
│                       # test_personality.py, test_pause.py, test_starter.py
├── integration/
│   ├── test_agent_feed.py
│   ├── test_chat_log.py
│   ├── test_direct_message_kind.py
│   ├── test_network_stop.py
│   ├── test_ollama_replier.py
│   ├── test_origin_policy.py
│   ├── test_pause_cancels_reply.py
│   ├── test_presence.py
│   ├── test_storage_boundary.py
│   └── test_websocket_transport.py
└── e2e/
    ├── test_manager_worker.py
    └── test_process_exit_status.py
```

---

## 🤝 Contributing

Got a new backend? Found a bug? PRs are welcome. Ensure:
1. Tests pass (`python -m pytest -q`)
2. Code compiles (`python -m compileall -q src tests`)
3. Lint passes (`python -m ruff check .`)
4. Documentation matches implementation

---

## 📝 License

Distributed under **All Rights Reserved**. See [LICENSE](LICENSE) for more information.

---

<div align="center">
  <i>Built with ☕ and ⚡ by Thomas Mixon</i>
</div>