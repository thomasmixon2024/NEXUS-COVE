# Repository Guidelines

## Project Structure & Module Organization

`src/nexus_cove` is organized by responsibility: `core/` holds domain models and protocol definitions, `orchestration/` manages manager scheduling and task routing, `agents/` owns worker lifecycle and execution backends, `transport/` handles WebSocket connections, `storage/` contains SQLite persistence, `observability/` logs and metrics, `config/` validates runtime config, and `api/` is reserved for future read-only HTTP surfaces. Keep cross-layer boundaries intact; do not let transport or storage code own scheduling logic. The default server binds to `127.0.0.1` and has no auth or TLS, so keep it local-only.

## Build, Test, and Development Commands

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

Single-test example:

```powershell
python -m pytest tests/integration/test_websocket_transport.py -q
```

Runtime entry points:

```powershell
python -m nexus_cove.transport.websocket.server
python -m nexus_cove.orchestration.manager
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

## Coding Style & Naming Conventions

This project targets Python 3.11-3.13, uses `ruff` rules `E`, `F`, `I`, `B`, and `UP`, and keeps line length at 100 characters. EditorConfig enforces UTF-8, LF endings, 4-space indentation, and 2-space indentation for YAML/TOML/JSON. `.pre-commit-config.yaml` also runs whitespace fixers, YAML/TOML validation, large-file checks, merger-conflict detection, and `compileall`.

## Testing Guidlines

`pytest` is the test harness; the repo organizes tests in `tests/unit`, `tests/integration`, and `tests/e2e`. Treat the suite as the source of truth: failing tests must exit non-zero, and real behavior is required rather than mock-only assertions.

## Commit & Pull Request Guidelines

Recent history uses terse, imperative subjects with prefixes such as `fix:`, `refactor:`, and `docs:`. Keep change sets focused and include the validation command(s) you ran. No PR template was found under `.github`.
