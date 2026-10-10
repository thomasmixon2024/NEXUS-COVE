# Architecture Overview

```text
Web/UI Client
     |
     v
WebSocket Transport
     |
     v
Orchestration Manager
  |        |        |
  |        |        +--> Scheduler / Routing Policy
  |        +-----------> Agent Registry
  +--------------------> Task Registry
             |
             v
        Agent Worker
             |
             v
      Execution Backend
             |
             +--> TaskResult
             |
             +--> Metrics / Logs
             |
             v
          SQLite
```

No layer is allowed to reach around another layer for convenience.
