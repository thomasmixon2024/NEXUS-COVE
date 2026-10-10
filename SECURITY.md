# Security

## Current posture

NEXUS COVE is designed for **localhost development only**.

- The WebSocket endpoint binds to `127.0.0.1` by default.
- There is **no authentication, authorization, or encryption (TLS/WSS)**.
- The server must **not** be exposed to a LAN or the public internet.

Do not change the bind address to `0.0.0.0` or a routable interface without first implementing the controls listed below.

## Threat model (local development)

| Asset | Risk if exposed | Current mitigation |
|-------|-----------------|--------------------|
| Task/result data in SQLite | Confidentiality loss | Localhost-only bind |
| Agent control plane (`control` / pause / stop) | Integrity / availability | Localhost-only bind |
| Chat and agent_feed traffic | Confidentiality loss | Localhost-only bind |
| Process execution via worker backends | Code execution | Deterministic/test backend only in the distributed tree |

## Required before any network deployment

Before binding to a non-loopback interface or publishing a port, implement and document:

1. Authenticated client identities
2. Authorization for control and task actions
3. TLS / WSS
4. Payload size limits and rate limiting
5. Secret management (no credentials in source or logs)
6. A written threat model for agent execution backends
7. An ADR recording the security design decision

## Reporting a vulnerability

If you discover a security issue in the localhost design or in any future authenticated surface, please report it privately to the maintainers. Do not open a public issue that includes exploit details until a fix is available.

## Scope

This policy applies to the canonical `src/nexus_cove` tree and the supporting scripts under `scripts/`. Third-party model servers (for example Ollama) are outside the scope of this document and must be secured according to their own guidance.
