<div align="center">
  <img src="assets/NEXUS-COVE-LOGO.jpg" alt="NEXUS-COVE Logo" width="420">

  <h1>NEXUS-COVE</h1>

  <p><strong>A lightweight, async Python framework for running local AI agents.</strong><br>
  <em>Zero cloud. Zero API keys. Absolute edge.</em></p>

  [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
  [![Ollama](https://img.shields.io/badge/Backend-Ollama-black.svg)](https://ollama.com)
  [![Termux Ready](https://img.shields.io/badge/Android-Termux-green.svg)](https://termux.dev)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
</div>

---

## 🧠 What is this?

**NEXUS-COVE** is an asynchronous agent framework designed to be absurdly lightweight. It strips out the bloat of modern AI wrappers and gets straight to the point: connecting your agents to local, offline LLMs so they can talk to each other without paying a dime to OpenAI.

Built for the edge. Built for speed. Built to run anywhere Python runs.

---

## 🔥 THE TERMUX FLEX 🔥

We didn't just build this for 64-core server racks. We built it to run in your pocket.

> **Benchmark:** Tested live on an **Android ARM64 device via Termux**.
> **Model:** `qwen2.5:0.5b` (Q4_K_M)
> **Latency:** **1.57 seconds** (Warm) ⚡

If it runs on Android, it'll run on your toaster.

---

## ⚡ Core Features

* **True Async:** Built from the ground up with `asyncio` and `aiohttp` for non-blocking agent chatter.
* **Backend Agnostic:** Ships with native support for Ollama.
* **No API Keys:** Your data stays on your machine. Period.
* **Modular:** Want to add a new LLM backend? Drop it in `src/nexus_cove/agents/backends/`.
* **Python 3.14 Ready:** Constraint tested and verified up to `<3.15`.

---

## 🚀 Quick Start (The 10-Second Setup)

**Don't worry, you don't need to be a DevOps wizard to try this.** We built a one-click script that does *everything* for you (starts Ollama, pulls the model, installs dependencies, and runs the test).

```bash
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE
./run_demo.sh
```

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

<details>
<summary><b>🛠️ Prefer to do it manually? Click here to expand.</b></summary>

<br>

**1. Prerequisites**

You need [Ollama](https://ollama.com/) installed and running on your host machine.

```bash
# Start the Ollama daemon
ollama serve

# Pull the lightweight test model
ollama pull qwen2.5:0.5b
```

**2. Install NEXUS-COVE**

Clone the repo and install it in editable mode:

```bash
git clone https://github.com/thomasmixon2024/NEXUS-COVE.git
cd NEXUS-COVE
pip install -e ".[dev]"
```

**3. Run the Verification Test**

```bash
python tests/termux_ollama_test.py
```

</details>

---

## 📱 Mobile / Termux Setup

Want to run it on Android? We wrote the whole playbook for it.

👉 [Read the Termux + Ollama Setup Guide](docs/operations/termux-ollama.md)

---

## 📂 Project Structure

```text
NEXUS-COVE/
├── docs/operations/       # Deployment guides (Termux, etc.)
├── src/nexus_cove/        # Core framework
│   └── agents/backends/   # LLM integrations (Ollama)
├── tests/                 # Pytest suite & standalone scripts
├── run_demo.sh            # One-click verification script
└── pyproject.toml         # PEP 621 packaging
```

---

## 🤝 Contributing

Got a new backend? Found a bug? PRs are wide open. Just make sure your tests pass and your code is formatted.

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

<div align="center">
  <i>Built with ☕ and ⚡ by Thomas Mixon</i>
</div>
