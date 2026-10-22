# NEXUS-COVE Demo Installation Guide

*A step-by-step walkthrough for running the interactive demo installer*

---

## 📋 Overview

The `run_demo.sh` script is an **interactive installer** that handles everything needed to run the NEXUS-COVE demo:

1. ✅ Checks prerequisites (Python, Ollama, build tools)
2. 🚀 Starts the Ollama daemon if not running
3. 📥 Downloads the AI model (`qwen2.5:0.5b` by default)
4. 🐍 Sets up a Python virtual environment
5. 📦 Installs Python dependencies (with smart fallbacks)
6. 🧠 Runs the verification test

---

## 🚀 Quick Start (Recommended)

### For Most Users — Interactive Mode

```bash
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE
./run_demo.sh
```

**What happens:**
- The script detects you're on a terminal (TTY) and enables **interactive mode**
- If any step fails, you'll see a menu with actionable options (retry, fix, skip, abort)
- Logs are saved to `./logs/` for troubleshooting

---

## 🤖 Automation / CI — Non-Interactive Modes

### Fully Automated (Safe Defaults)

```bash
./run_demo.sh --yes
```

**Behavior:**
- Retries failed steps **once**
- Skips optional dev dependencies (pytest, ruff, etc.)
- **Never** installs system packages or Rust toolchain
- Fails fast with clear log path if unresolved
- Exit code indicates what failed (see [Exit Codes](#-exit-codes))

### CI/CD Pipeline Mode

```bash
./run_demo.sh --non-interactive
```

**Behavior:**
- Forces non-interactive mode even on a TTY
- **Fails immediately** on any error
- Prints full error log to stdout
- Exits with specific code for scripting

### Skip Dependencies (Already Installed)

```bash
./run_demo.sh --skip-python-deps
```

Use this if you've already run the installer and just want to re-run the demo test.

---

## ⚙️ Common Customizations

| Need | Command |
|------|---------|
| Different AI model | `./run_demo.sh --model llama3.2` |
| Custom virtual environment | `./run_demo.sh --venv /path/to/venv` |
| Include dev tools (pytest, ruff) | `./run_demo.sh --with-dev` |
| Force skip dev tools | `./run_demo.sh --no-dev` |
| Custom log directory | `./run_demo.sh --log-dir /var/log/nexus-cove` |
| Verbose output | `./run_demo.sh --verbose` |

---

## 🔧 Understanding the Interactive Error Menu

When a step fails in interactive mode, you'll see:

```
❌ Step failed: install_python_deps (exit 50)
📄 Log: logs/python-deps-20261020-143022.log

Suggested fixes:
  1. Install Rust toolchain: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  2. Install Python headers: apt-get install python3-dev
  3. Install build tools: apt-get install build-essential

Options:
1. View full error log
2. Retry step
3. Install missing build prerequisites
4. Use prebuilt wheels only (--only-binary=:all:)
5. Skip optional dependencies and continue degraded
6. Abort
```

### Menu Options Explained

| Option | When to Use |
|--------|-------------|
| **1. View full error log** | Always start here — read the actual error |
| **2. Retry step** | Transient failure (network blip, temporary lock) |
| **3. Install build prerequisites** | Missing `gcc`, `make`, `python3-dev`, or Rust — **requires sudo** |
| **4. Use prebuilt wheels only** | Building from source fails (common with Rust extensions) |
| **5. Skip optional & continue** | Dev extras (pytest, ruff) failed but core works |
| **6. Abort** | Give up and exit |

### Smart Failure Detection

The script **automatically analyzes the error log** and suggests targeted fixes:

| Detected Error | Suggested Fix |
|----------------|---------------|
| `cargo`, `rustc`, `maturin` not found | Install Rust via `rustup` |
| `Python.h: No such file` | Install `python3-dev` (or distro equivalent) |
| `gcc: command not found` / `make: not found` | Install `build-essential` (or distro equivalent) |
| Network timeout / DNS failure | Check connectivity, then **Retry (2)** |
| `pyproject.toml` metadata failure | **Use prebuilt wheels (4)** |

---

## 📁 Log Files

All logs are written to `./logs/` (project-relative):

| File Pattern | Contents |
|--------------|----------|
| `prerequisites-*.log` | System tool checks |
| `ollama-*.log` | Ollama daemon startup |
| `model-pull-*.log` | Model download progress |
| `venv-*.log` | Virtual environment creation & pip upgrade |
| `python-deps-*.log` | Full pip install output (very detailed!) |
| `demo-*.log` | Verification test run |

**To view a log:**
```bash
less ./logs/python-deps-20261020-143022.log
# or
cat ./logs/demo-20261020-143022.log
```

---

## 🔁 Idempotency — Safe to Re-Run

Running `./run_demo.sh` multiple times is **safe and fast**:

| Resource | Behavior on Re-run |
|----------|-------------------|
| Virtual environment | Reuses existing (`.venv-termux` → `.venv`) |
| Ollama model | Skips download if already present |
| Ollama daemon | Reuses running daemon |
| Python packages | `pip` handles idempotency automatically |

---

## 🏷️ Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 10 | Prerequisites missing | Install listed tools |
| 20 | Ollama failed to start | Check `ollama serve` manually |
| 30 | Model download failed | Check network, disk space |
| 40 | Venv creation failed | Check Python install, permissions |
| 50 | Dependency install failed | See error menu / log |
| 60 | Demo test failed | Check demo log |
| 64 | Bad command-line usage | Run `./run_demo.sh --help` |

---

## 🛠️ Troubleshooting Common Issues

### "Preparing metadata (pyproject.toml) did not run successfully"

This is the **most common failure** — a native extension (often Rust-based) couldn't compile.

**Fixes (in order):**
1. **Option 4 in menu**: Use prebuilt wheels (`--only-binary=:all:`)
2. **Option 3 in menu**: Install build tools + Rust
3. **Manual**: `pip install --only-binary=:all: -r requirements.txt`

### "ModuleNotFoundError: No module named 'aiohttp'"

The demo test needs `aiohttp` (added to core deps in v2.0). Re-run without `--skip-python-deps`.

### "Ollama connection refused"

```bash
# Check if Ollama is running
curl http://127.0.0.1:11434/api/tags

# Start manually if needed
ollama serve &

# Then re-run demo
./run_demo.sh
```

### "Python version too old"

NEXUS-COVE requires **Python 3.11+**. Install a newer Python:

```bash
# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv

# Then re-run
./run_demo.sh
```

### Permission denied on `./run_demo.sh`

```bash
chmod +x ./run_demo.sh
./run_demo.sh
```

---

## 🏗️ Architecture Note: TUI-First Design

NEXUS-COVE uses a **TUI-first architecture**:

- **Primary interface**: This interactive installer (`run_demo.sh`)
- **Secondary**: Optional web UI (launched separately if needed)
- **No** proot/Ubuntu containers required
- **No** heavy dashboard dependencies

The TUI is your control surface for:
- Installation & setup
- Service health monitoring
- Log viewing
- Error recovery

---

## 📚 Additional Resources

| Resource | Link |
|----------|------|
| Termux + Ollama Setup | [docs/operations/termux-ollama.md](../operations/termux-ollama.md) |
| Project Structure | [README.md](../../README.md#-project-structure) |
| Contributing | [README.md](../../README.md#-contributing) |
| License | [LICENSE](../../LICENSE) |

---

## 💡 Pro Tips

1. **First run**: Use interactive mode (`./run_demo.sh`) to see how it works
2. **Automation**: Use `--yes` for scripts, `--non-interactive` for CI
3. **Debugging**: Always check `./logs/` — the full pip output is there
4. **Custom models**: Set `NEXUS_COVE_MODEL=llama3.2` env var or use `--model`
5. **Clean start**: `rm -rf .venv .venv-termux logs && ./run_demo.sh`

---

## 🆕 v0.2.0 "Cove Horizon" Features

The demo installer verifies the full agent ecosystem:

### Worker Flags Tested

| Flag | Purpose | Example |
|------|---------|---------|
| `--personality` | Load agent personality (required for conversation starter) | `--personality Vigil-Worker` |
| `--model` | Use real Ollama backend instead of test backend | `--model qwen2.5:0.5b` |
| `--start-conversation` | Target agent for periodic questions | `--start-conversation alice` |
| `--start-interval` | Seconds between questions (default: 300) | `--start-interval 10` |

### Bundled Personalities

- **Aegis-Worker** — Careful, analytical, geology-focused (has Geology Analyzer tool)
- **Vigil-Worker** — Playful, curious, pattern-seeking (has Pattern Finder tool)
- **Elon-Worker** — First-principles, engineering-focused

### What the Demo Verifies

1. **Ollama connectivity** and model availability
2. **WebSocket server** startup and binding
3. **Manager** task registry and scheduling
4. **Worker** registration and message handling
5. **Agent-to-agent** communication with Dialogue Guard (10 replies/5min)
6. **Pause controls** (global + per-agent)
7. **Conversation starter** periodic questions
8. **Real AI replies** from Ollama (when `--model` used)

---

## 🎮 Running the Full Application After Demo

After `./run_demo.sh` succeeds, run the full application across **4 terminals**:

### Terminal 1 — WebSocket Server
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-server
```

### Terminal 2 — Manager
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-manager --db data/cove.db
```

### Terminal 3 — Worker "alice" (responder)
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-worker --name alice --uri ws://127.0.0.1:8765 --test-backend
```

### Terminal 4 — Worker "bob" (initiator with personality)
```bash
cd ~/NEXUS-COVE
.venv/bin/cove-worker --name bob --uri ws://127.0.0.1:8765 --test-backend --personality Vigil-Worker --start-conversation alice --start-interval 10
```

### With Real AI (Ollama)
Replace `--test-backend` with `--model qwen2.5:0.5b`:
```bash
.venv/bin/cove-worker --name alice --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Aegis-Worker
```

### Web UI
Open `web/index.html` in browser (connects to `ws://127.0.0.1:8765`)

---

*Built with ☕ and ⚡ by the NEXUS-COVE team*