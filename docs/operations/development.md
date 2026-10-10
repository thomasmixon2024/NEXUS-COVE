# Development Guide

## Install

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
```

## Verify

```bash
python -m compileall -q src tests
python -m pytest tests -q
python -m ruff check .
```

## Run locally

Start the WebSocket server first, then a worker and manager. The default endpoint is `ws://127.0.0.1:8765`.

```bash
python -m nexus_cove.transport.websocket.server
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
python -m nexus_cove.orchestration.manager
```

The worker refuses to start without `--test-backend`, because the deterministic backend is the only execution backend bundled with the project. The manager module does not submit tasks by itself; `scripts/diagnostics/check_roundtrip.py` submits one task and reports the result. Real model execution is not bundled into the core.
