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

### Agents respond with "X heard you" but won't converse

**Symptom:** Agents are connected and acknowledge messages (showing "Aegis-Worker heard you, T." etc.) but don't engage in real conversation.

**Cause:** Workers are running with `--test-backend` only, without `--model qwen2.5:0.5b`. The test backend only provides canned acknowledgment replies.

**Fix:** Launch workers with both flags:
```bash
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend --model qwen2.5:0.5b --uri ws://127.0.0.1:8765
```
Or simply use `./cove-testbed.sh` which configures this automatically.

---

## 🏗️ Architecture Note: Browser-First Design

NEXUS-COVE uses a **browser-first architecture**:

- **Primary interface**: Browser dashboard (`web/index.html` at `http://127.0.0.1:8080`)
- **Secondary**: Interactive installer (`run_demo.sh`) for setup/verification
- **Optional**: Four-session terminal workflow for headless/automation/debugging
- **No** proot/Ubuntu containers required
- **No** heavy dashboard dependencies (single-file HTML + Tailwind CDN)

The browser dashboard provides:
- Real-time chat with agents
- Agent pause/resume controls
- Mobile-friendly off-canvas sidebar
- Chat log save/download

---

## 🌐 Launching the Dashboard

After `run_demo.sh` completes (or manually with the model installed), launch the full stack with the browser UI:

```bash
./cove-testbed.sh    # starts server + manager + 3 workers + opens browser
./cove-kill.sh       # stops everything
```

This starts the WebSocket server, manager, 3 conversational workers (with `--model qwen2.5:0.5b`), and a static file server on port 8080, then opens the dashboard automatically.

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

*Built with ☕ and ⚡ by the NEXUS-COVE team*