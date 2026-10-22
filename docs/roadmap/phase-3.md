# Phase 3 — Observability Dashboard

**Status: Planned (Post v0.2.0)**

---

## ✅ What's Already Done (v0.2.0 "Cove Horizon")

The following observability features are **implemented and working** in v0.2.0:

| Feature | Module | Status |
|---------|--------|--------|
| **Structured Chat Log** | `observability/chatlog.py` | ✅ Complete |
| - JSONL append/read | | ✅ |
| - Bounded-tail reads for UI | | ✅ |
| - Downloadable as Markdown | | ✅ |
| **Runtime Metrics** | `observability/metrics.py` | ✅ Complete |
| - Task submitted/completed/failed counters | | ✅ |
| - Duration histograms | | ✅ |
| - Monotonic clock measurements | | ✅ |
| **Structured Logging** | `observability/logging.py` | ✅ Complete |
| - JsonFormatter with timestamps | | ✅ |
| - Monotonic timestamps | | ✅ |
| **Agent Feed** | `transport/websocket/server.py` | ✅ Complete |
| - Last 200 agent→agent messages | | ✅ |
| - Replayed to late-joining browsers | | ✅ |
| **Presence/Status Dots** | `transport/websocket/server.py` + UI | ✅ Complete |
| - Green/red per agent | | ✅ |
| - Updated via `presence` action | | ✅ |
| **SQLite Storage Stats** | `storage/sqlite.py` | ✅ Complete |
| - Task counts by status/agent | | ✅ |
| - Duration percentiles | | ✅ |
| **Session Continuity** | `agents/memory.py` | ✅ Complete |
| - Checkpoints | | ✅ |
| - Highlights extraction | | ✅ |
| - Session journal | | ✅ |

---

## 🎯 Phase 3 Scope: Observability Dashboard

The **Observability Dashboard** is a **read-only HTTP API + Web UI** that consumes the existing storage/observability interfaces — **not** a replacement for them.

### Planned Components

| Component | Description | Consumes |
|-----------|-------------|----------|
| **HTTP API** (`api/`) | Read-only REST endpoints | `Storage`, `ChatLog`, `RuntimeMetrics` |
| **Dashboard UI** | Real-time metrics visualization | HTTP API |
| **Historical Queries** | Time-range filtered metrics | SQLite Storage |
| **Agent Timeline** | Per-agent activity visualization | ChatLog + Memory |
| **System Health** | Process status, connection health | Manager + Server presence |

### API Endpoints (Planned)

```
GET  /api/v1/health              # System health
GET  /api/v1/agents              # Agent list with status
GET  /api/v1/agents/{id}/metrics # Per-agent metrics
GET  /api/v1/tasks               # Task list with filters
GET  /api/v1/tasks/{id}          # Task detail
GET  /api/v1/metrics/summary     # Aggregate metrics
GET  /api/v1/metrics/history     # Time-series data
GET  /api/v1/chatlog             # Paginated chat log
GET  /api/v1/chatlog/export      # Markdown export
```

### Dashboard Views (Planned)

1. **Overview** — System health, active agents, task throughput
2. **Agents** — Per-agent status, load, memory size, knowledge count
3. **Tasks** — Task pipeline visualization, duration distributions
4. **Conversations** — Chat log search, agent→agent flow diagrams
5. **Metrics** — Real-time charts (throughput, latency, errors)

---

## 🏗️ Architecture Principles

```
┌─────────────────────────────────────────────────────────────┐
│                    Observability Dashboard                  │
│  (HTTP API + Web UI) — NEW in Phase 3                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ READ ONLY
              ┌────────────┴────────────┐
              ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │  SQLite Storage │       │  ChatLog/       │
    │  (storage/)     │       │  Metrics        │
    │                 │       │  (observability/)│
    └─────────────────┘       └─────────────────┘
              ▲                         ▲
              │                         │
    ┌─────────┴─────────┐               │
    │   Manager/Worker  │               │
    │  (orchestration/  │               │
    │   agents/)        │               │
    └───────────────────┘               │
                                        │
                           ┌────────────┴────────────┐
                           ▼                         ▼
                    ┌─────────────┐         ┌─────────────┐
                    │  Transport  │         │   Web UI    │
                    │  (server)   │         │ (index.html)│
                    └─────────────┘         └─────────────┘
```

**Key Principle**: Dashboard is a **consumer** of existing interfaces. No changes to core, orchestration, agents, transport, or storage required.

---

## 📋 Implementation Checklist

### Phase 3.1: HTTP API Foundation
- [ ] `src/nexus_cove/api/` module structure
- [ ] FastAPI/Starlette read-only server
- [ ] Dependency injection for Storage, ChatLog, Metrics
- [ ] OpenAPI schema generation
- [ ] Unit tests for API endpoints

### Phase 3.2: Core Endpoints
- [ ] `/health` — process status, DB connectivity
- [ ] `/agents` — registry snapshot with capabilities
- [ ] `/tasks` — paginated, filterable task list
- [ ] `/metrics/summary` — aggregate counters/histograms
- [ ] `/chatlog` — paginated, searchable log

### Phase 3.3: Dashboard UI
- [ ] Single-page dashboard (separate from `web/index.html`)
- [ ] Real-time updates via Server-Sent Events or polling
- [ ] Charts: throughput, latency, error rates
- [ ] Agent cards with status/memory/knowledge
- [ ] Task timeline with status transitions

### Phase 3.4: Advanced Features
- [ ] Historical queries with time ranges
- [ ] Agent conversation flow visualization
- [ ] Export endpoints (JSON, CSV, Markdown)
- [ ] Alerting thresholds (configurable)

---

## 🔗 Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `fastapi` | ≥0.110 | HTTP API framework |
| `uvicorn` | ≥0.29 | ASGI server |
| `pydantic` | ≥2.7 | Request/response validation |
| `httpx` | ≥0.27 | Test client |
| Chart.js / similar | latest | Dashboard charts (via CDN) |

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dashboard = [
  "fastapi>=0.110,<1",
  "uvicorn>=0.29,<1",
  "pydantic>=2.7,<3",
  "httpx>=0.27,<1",
]
```

---

## 🚀 Running the Dashboard (Future)

```bash
# Install dashboard extras
pip install -e ".[dashboard]"

# Start API server (read-only, no auth - local only)
python -m nexus_cove.api.server --db data/cove.db --chatlog logs/nexus_chat.jsonl

# Open dashboard UI
# http://localhost:8081 (or configured port)
```

---

## 📝 Notes

- **No authentication** in Phase 3 — binds to loopback only (`127.0.0.1`)
- **Read-only** — no write endpoints, no control plane
- **Consumes existing interfaces** — zero changes to v0.2.0 core
- **Optional dependency** — core framework works without dashboard extras
- **Separate process** — runs alongside server/manager/workers

---

## 🗓️ Timeline Estimate

| Phase | Effort | Target |
|-------|--------|--------|
| 3.1 API Foundation | ~1 week | Post v0.2.0 |
| 3.2 Core Endpoints | ~1 week | |
| 3.3 Dashboard UI | ~2 weeks | |
| 3.4 Advanced Features | ~1 week | |
| **Total** | **~5 weeks** | **v0.3.0** |

---

*Last updated: 2026-10-21 (v0.2.0 "Cove Horizon" release)*