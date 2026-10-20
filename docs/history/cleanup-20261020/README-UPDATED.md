
# NEXUS COVE

````markdown
NEXUS COVE is an experimental local multi-agent orchestration framework. It coordinates tasks between locally hosted agents using explicit domain models, a WebSocket transport layer, orchestration logic, storage, and observability.

## About The Project

This repository is the canonical source of truth for the project. It is organized around a small set of responsibilities:

- `core/`: domain models, protocol messages, and exceptions
- `orchestration/`: task routing, scheduling, and manager lifecycle
- `agents/`: worker lifecycle and execution backends
- `transport/`: WebSocket connection and message handling
- `storage/`: persistence and SQLite access
- `observability/`: logs, health checks, and runtime metrics
- `config/`: validated runtime configuration
- `api/`: reserved for future read-only HTTP surfaces

The default server is local-only and intentionally does not enable authentication or TLS.

## Architecture

```text
Client / UI
    |
    v
Transport (WebSocket)
    |
    v
Orchestration Manager -> Scheduler/Router -> Agent Registry
    |                                  |
    |                                  v
    |                            Agent Backend
    v
Task/Result domain models
    |
    +--> Storage (SQLite)
    +--> Observability (logs/metrics/health)
```

## Built With

- Python 3.11+
- WebSockets
- Pydantic
- SQLite
- pytest
- Ruff
- PowerShell 7+ (Windows)

## Project Structure

```text
src/
  nexus_cove/
    agents/
    config/
    core/
    observability/
    orchestration/
    storage/
    transport/
tests/
scripts/
requirements.txt
pyproject.toml
```

## Getting Started

### Prerequisites

Ensure you have the following installed:

- Python 3.11+
- Git
- PowerShell 7+ on Windows
- A local terminal environment

### Installation

1. Clone the repository.

```powershell
git clone https://github.com/thomas-mixon/nexus-cove.git
cd nexus-cove
```

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

1. Install dependencies.

```powershell
python -m pip install -e ".[dev]"
```

If needed, you can also install the base requirements file:

```powershell
python -m pip install -r requirements.txt
```

## Development Commands

From the repository root:

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

## Usage

1. Start the local WebSocket server.

```powershell
python -m nexus_cove.transport.websocket.server
```

1. Run the orchestration manager.

```powershell
python -m nexus_cove.orchestration.manager
```

1. Run a worker.

```powershell
python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
```

1. Run the test suite.

```powershell
python -m pytest tests -q
```

## Testing Policy

Tests are the source of truth for behavior. A passing test must exercise real behavior, and a failing test must exit non-zero.

Test levels:

- `tests/unit/`: isolated deterministic behavior
- `tests/integration/`: real service and boundary validation
- `tests/e2e/`: end-to-end manager-to-worker workflows

## Roadmap

- [x] Establish modular directory layout
- [x] Add local agent and WebSocket communication scaffolding
- [x] Add setup helper scripts
- [ ] Expand project documentation and usage examples
- [ ] Add more advanced orchestration and routing rules
- [ ] Grow integration and end-to-end coverage

## Contributing

Contributions are welcome. Keep changes focused, add or update tests for behavior changes, and validate the relevant commands before submitting a PR.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch.
5. Open a pull request.

## License

This project is distributed under the MIT License. See `LICENSE` for more information.

## Contact

- Thomas Mixon
- GitHub: [https://github.com/thomas-mixon](https://github.com/thomas-mixon)
- Project: [https://github.com/thomas-mixon/nexus-cove](https://github.com/thomas-mixon/nexus-cove)
````

This removes the final MD041 issue and keeps the list style compliant with MD029.
