# Security

Cove is currently designed for localhost development. The WebSocket endpoint has no authentication or authorization and must not be exposed to an untrusted network.

Before LAN/internet deployment, implement authenticated identities, authorization, TLS/WSS, payload limits, rate limiting, secret management, and a threat model for agent execution.
