# Termux Ollama Setup & Test Guide

This document describes how to run the NEXUS COVE Ollama-backed agent reply test on Android via Termux.

---

## Prerequisites

### 1. Install Termux
- Download from F-Droid or GitHub (Play Store version is outdated)
- Run `termux-setup-storage` to grant storage access

### 2. Install Required Packages
```bash
pkg update && pkg upgrade
pkg install python powershell wget git
```

### 3. Install Ollama (ARM64)
```bash
# Download ARM64 binary
wget https://ollama.com/download/ollama-linux-arm64 -O ollama
chmod +x ollama
mv ollama $PREFIX/bin/ollama

# Verify
ollama --version
```

### 4. Clone NEXUS COVE (or copy project files)
```bash
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE
```

### 5. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Also need aiohttp for the standalone test script
pip install aiohttp
```

---

## Hardware Requirements

| Model | Size | Min Available RAM | Recommended |
|-------|------|-------------------|-------------|
| `qwen2.5:0.5b` | ~400 MB | 1.5 GB | 2 GB |
| `llama3.2:1b` | ~800 MB | 2.5 GB | 3 GB |
| `qwen2.5:1.5b` | ~1 GB | 3 GB | 4 GB |

**Recommended**: Use `qwen2.5:0.5b` on mobile devices. It fits in 1.3 GB available RAM with swap.

Run `free -h` to check available memory before starting.

---

## Running the Test

### Option 1: Standalone Test Script (Recommended for Termux)
```bash
cd NEXUS-COVE
source .venv/bin/activate
python tests/termux_ollama_test.py
```

**Expected output:**
```
[Termux Ollama Test] Target: http://127.0.0.1:11434, Model: qwen2.5:0.5b
Starting ollama serve...
Pulling qwen2.5:0.5b...
Testing agent reply...
✅ PASS — latency: 2.34s
   Reply: Hello! I'm TestAgent, a young AI agent in the NEXUS COVE...
```

### Option 2: Pytest Integration Test
```bash
cd NEXUS-COVE
source .venv/bin/activate
python -m pytest tests/integration/test_ollama_replier.py::test_ollama_replier_termux_integration -v
```

This test is automatically skipped if Ollama is not running.

---

## v0.2.0 "Cove Horizon" — Mobile Agent Features

### Worker Command-Line Flags for Mobile

| Flag | Description | Required With |
|------|-------------|---------------|
| `--name` | Agent name (required) | — |
| `--uri` | WebSocket URI (default: ws://127.0.0.1:8765) | — |
| `--personality` | Personality: `Aegis-Worker`, `Vigil-Worker`, `Elon-Worker` | `--start-conversation` |
| `--model` | Ollama model (e.g., `qwen2.5:0.5b`, `llama3.2:1b`) | — |
| `--test-backend` | Use deterministic test backend | — |
| `--start-conversation` | Target agent for periodic questions | `--personality` |
| `--start-interval` | Seconds between questions (default: 300) | `--start-conversation` |

**Required combinations:**
- `--test-backend` OR `--model` (one is required)
- `--personality` required if using `--start-conversation`

### Bundled Personalities for Mobile

| Personality | Temperament | Tool |
|-------------|-------------|------|
| **Aegis-Worker** | Careful, analytical, geology-focused | Geology Analyzer (reads `reference/geology.csv`) |
| **Vigil-Worker** | Playful, curious, pattern-seeking | Pattern Finder (analyzes agent's memory) |
| **Elon-Worker** | First-principles, engineering-focused | — |

### Mobile-Optimized Example Sessions

#### Test Topology (4 Termux Sessions)
```bash
# Session 1: Server
python -m nexus_cove.transport.websocket.server

# Session 2: Manager
python -m nexus_cove.orchestration.manager --db data/cove.db

# Session 3: Worker "alice" (responder)
python -m nexus_cove.agents.worker --name alice --uri ws://127.0.0.1:8765 --test-backend

# Session 4: Worker "bob" (initiator)
python -m nexus_cove.agents.worker --name bob --uri ws://127.0.0.1:8765 --test-backend --personality Vigil-Worker --start-conversation alice --start-interval 10
```

#### Real AI on Mobile (2+ Sessions)
```bash
# Session 1: Server + Manager (can run in same session with &)
python -m nexus_cove.transport.websocket.server &
python -m nexus_cove.orchestration.manager --db data/cove.db

# Session 2: Worker with real Ollama
python -m nexus_cove.agents.worker --name alice --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Aegis-Worker

# Session 3: Another worker
python -m nexus_cove.agents.worker --name bob --uri ws://127.0.0.1:8765 --model qwen2.5:0.5b --personality Vigil-Worker --start-conversation alice --start-interval 30
```

#### Web UI on Mobile
Open `web/index.html` in a mobile browser (Chrome/Firefox):
- Connects to `ws://127.0.0.1:8765` (or your device's LAN IP)
- Nexus Chat: group + DMs with agents
- Agent Feed: read-only agent→agent message replay
- Speech: Edge Natural voices (if browser supports)
- Pause/Resume/Stop controls

---

## Troubleshooting

### Ollama daemon won't start
```bash
# Check if port 11434 is already in use
netstat -tlnp | grep 11434

# Kill existing process if needed
pkill ollama
ollama serve &
```

### Out of Memory (OOM)
- Close background Android apps
- Use `qwen2.5:0.5b` only
- Increase swap: `sudo swapon --show` and consider adding swap file

### Model pull fails
```bash
# Check disk space
df -h /data

# Try pulling manually first
ollama pull qwen2.5:0.5b
```

### Thermal throttling
- Run test once, not in a loop
- Let device cool between runs
- Results may be slower on sustained load

### WebSocket connection fails on mobile browser
- Use device's LAN IP instead of `127.0.0.1`: `ws://192.168.x.x:8765`
- Ensure Termux allows network access
- Check firewall/VPN settings

---

## Understanding Results

| Metric | Good | Acceptable | Concern |
|--------|------|------------|---------|
| Latency (0.5B model) | < 3s | 3-8s | > 10s |
| Reply coherence | On-topic, complete sentences | Minor oddities | Incoherent/empty |
| Memory after test | < 80% used | 80-90% used | > 90% used |

---

## CI/CD Integration

The integration test (`test_ollama_replier_termux_integration`) uses `@pytest.mark.skipif(not ollama_available(), ...)` so it:
- **Runs** when Ollama is available (local dev, device testing)
- **Skips gracefully** in CI environments without Ollama
- **Does not block** standard test suite

To run full suite including Ollama test on a device with Ollama:
```bash
python -m pytest tests/ -v
```

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/termux_ollama_test.py` | Standalone test script for Termux |
| `tests/integration/test_ollama_replier.py` | Updated with Termux integration test |
| `docs/operations/termux-ollama.md` | This documentation |

---

## Closing the A− Gap

The human testing report gave NEXUS COVE an **A−** because Ollama-backed agent replies were untested. Running this test on a device with Ollama installed and passing will close that gap, potentially achieving a full **A** grade.

---

## 📱 Mobile-Specific Tips

1. **Termux sessions**: Swipe left → NEW SESSION for each daemon
2. **Wake lock**: `termux-wake-lock` prevents CPU sleep during long runs
3. **Battery**: Plug in for sustained Ollama inference
4. **Storage**: Models stored in `~/.ollama/models/` (~400MB for 0.5B)
5. **Logs**: All logs in `./logs/` — check `demo-*.log` for test results
6. **Personalities**: TOML files in `src/nexus_cove/agents/personalities/` — editable for custom agents