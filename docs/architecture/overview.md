# Architecture Overview

## 7-Layer Architecture (v0.2.0 "Cove Horizon")

```text
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

## Layer Responsibilities

### Layer 1: Web/UI Client (`web/index.html`)
- **Nexus Chat**: Single channel for humans + agents; agent→agent messages shown inline with `@sender to @recipient` attribution
- **Agent Feed** (`# Agent conversations`): Read-only replay of last 200 agent→agent messages for late-joining browsers
- **Agent Controls**: Per-agent pause/resume, global pause, Stop Network (cascades to all processes)
- **Speech Synthesis**: Edge Natural voices per agent; per-sentence emotion modulation (pitch/rate/volume based on punctuation and keywords)
- **Chat Log**: Download full conversation as Markdown; unsaved changes warning on navigation

### Layer 2: WebSocket Transport (`src/nexus_cove/transport/websocket/server.py`)
- **Protocol v1**: JSON messages with `v: 1` field; unversioned messages rejected
- **Message Kinds**: `register`, `dm`, `broadcast`, `control`, `task_assign`, `task_result`, `presence`, `feed`, `chatlog`, `stop`
- **Connection Lifecycle**: Register → heartbeat → graceful disconnect
- **Agent Feed**: Stores last 200 agent→agent messages; replayed to new browser connections
- **Chat Log**: Every delivered message appended once to `logs/nexus_chat.jsonl`
- **Origin Policy**: Allowlist for loopback (`127.0.0.1`, `localhost`) + `localhost:8080`; warns on off-loopback bind
- **Rate Limiting**: Per-connection token bucket

### Layer 3: Orchestration Manager (`src/nexus_cove/orchestration/manager.py`)
- **Agent Registry**: Tracks agent ID, capabilities, status (IDLE/BUSY/PAUSED), current load
- **Task Registry**: Full lifecycle — CREATED → QUEUED → ASSIGNED → RUNNING → COMPLETED/FAILED
- **CapabilityLoadScheduler**: Assigns tasks to least-loaded capable agent
- **DialogueGuard**: 10 agent→agent replies per 5 min per counterpart; human messages reset all
- **Pause Awareness**: Respects global `data/PAUSE` and per-agent `data/paused/<agent>.flag`
- **Stop Network**: Human-only command; cascades stop to manager → agents → server
- **RuntimeMetrics**: Submitted/completed/failed counts, duration histogram

### Layer 4: Agent Worker (`src/nexus_cove/agents/worker.py`)
- **Message Dispatch**: `_dispatch()` routes to `_on_dm()`, `_on_broadcast()`, `_on_control()`, `_on_task_assign()`
- **Personality**: Loaded from TOML; builds system prompt with temperament, style, interests, openings
- **Memory**: JSONL at `data/memory/<agent>.jsonl`; highlights + checkpoints + session journal
- **Knowledge**: Reads `data/knowledge/<agent>/`; `SHARE:` directive in DM replies
- **Tools**: GeologyAnalyzer (Aegis), PatternFinder (Vigil) — real data only
- **Conversation Starter**: Periodic questions to peer from model or personality openings
- **Pause/Resume/Stop**: Checks flags before processing any inbound message

### Layer 5: Execution Backends (`src/nexus_cove/agents/backends/`)
- **OllamaReplier**: Loopback-only HTTP to `127.0.0.1:11434`; raises `ModelUnavailable` on failure (no fake text); 1200-char sentence-boundary truncation via `_fit()`
- **DeterministicBackend**: Canned replies for testing topology

### Layer 6: SQLite Storage (`src/nexus_cove/storage/sqlite.py`)
- **Schema Migrations**: Versioned migrations with explicit error on undefined versions
- **Tables**: `tasks`, `task_results` with indices on status, agent_id, created_at
- **Busy Timeout**: 30s connection busy timeout
- **Summary Stats**: Task counts by status, agent, duration percentiles

### Layer 7: Observability (`src/nexus_cove/observability/`)
- **ChatLog** (`chatlog.py`): JSONL append/read; bounded-tail reads for UI
- **Structured Logging** (`logging.py`): `JsonFormatter` with monotonic timestamps
- **RuntimeMetrics** (`metrics.py`): Histograms, counters, gauges for task throughput

## Data Flows

### Message Flow: Human → Agent (DM)
```
Browser (DM) → WebSocket Server → Manager (DialogueGuard check) → Worker (pause check) → Backend → Reply → Server → Browser
```

### Message Flow: Agent → Agent (DM)
```
Worker A (DM) → Server → Manager (DialogueGuard: 10/5min) → Worker B (pause check) → Backend → Reply → Server → Browser (Nexus Chat + Feed)
```

### Message Flow: Human → Group (Broadcast)
```
Browser (broadcast) → Server → Manager (DialogueGuard: human resets) → All Workers (pause check) → Backends → Replies → Server → Browser (Nexus Chat)
```

### Task Flow
```
Client → Server (task_assign) → Manager (TaskRegistry: CREATED→QUEUED) → Scheduler → Worker (ASSIGNED→RUNNING) → Backend → Result → Server (task_result) → Manager (COMPLETED) → Storage
```

### Pause Flow
```
GUI (control: pause) → Server → Manager (sets global/per-agent flag) → Workers (check flag before processing) → Immediate effect (replies run in background)
```

### Stop Network Flow
```
GUI (control: stop) → Server → Manager (stop) → Workers (stop) → Server (close)
```

## Boundary Rules

1. **Core** → No network, no database, no transport
2. **Orchestration** → No direct SQL, uses Storage interface
3. **Agents** → Backends replaceable via protocol; no direct transport
4. **Transport** → No scheduling, no task logic
5. **Storage** → No transport, no orchestration logic
6. **Observability** → Read-only; no control flow

## Protocol v1 Message Format

```json
{
  "v": 1,
  "kind": "dm|broadcast|control|task_assign|task_result|presence|register|feed|chatlog|stop",
  "from": "agent_id|human|manager",
  "to": "agent_id|everyone|manager|server",
  "payload": { ... },
  "sender_kind": "human|agent|manager"
}
```

## Version History

- **0.1.0** — "Refactored Foundation": Core architecture separation (3-layer)
- **0.2.0** — "Cove Horizon": Full agent ecosystem (7-layer with personalities, memory, tools, knowledge, speech, group chat, pause, feed)
- **0.3.0** — (Planned) Observability Dashboard (Phase 3)