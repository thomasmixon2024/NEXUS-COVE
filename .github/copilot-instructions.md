# NEXUS COVE Copilot instructions

This repository is the canonical source of truth for the NEXUS COVE multi-agent orchestration framework. Follow the project rules in AGENTS.md and CLAUDE.md before making changes.

Core constraints:
- Respect the subsystem boundaries: core, orchestration, agents, transport, storage, observability, config, and api.
- Do not duplicate existing implementations or create alternate source trees.
- Do not use fake or synthetic telemetry.
- Do not claim verification without running the relevant test or validation command.
- Prefer the smallest reproducible fix and the smallest relevant test.
- Treat tests as the source of truth and ensure failing tests exit non-zero.
- Keep local-only defaults and avoid exposing unauthenticated services.

When helping with a bug or feature:
1. Identify the exact subsystem and the root cause.
2. Reproduce or model the failing behavior.
3. Add or update the smallest failing test when appropriate.
4. Implement the minimal root-cause fix.
5. Run the narrowest validation command that checks the changed behavior.
6. Report the exact evidence and remaining risks.

When working on the chat app or WebSocket networking:
- keep transport concerns out of orchestration logic
- keep scheduling logic out of transport/storage code
- do not allow stale temporary browser identities to masquerade as real users
- handle reconnect and stop conditions carefully
- ignore temporary names like user_... when showing chat participants

This file is for repository-wide guidance; specialized prompt packs below are for focused task modes.
