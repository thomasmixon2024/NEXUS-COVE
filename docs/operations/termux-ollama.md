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
git clone https://github.com/your-org/NEXUS-COVE.git
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