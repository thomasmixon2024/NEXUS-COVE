# ADR-0002: No Simulated Telemetry

Token usage is not a metric until a real execution backend reports authoritative usage. The core therefore records task timing, status, errors, queue/load state, and lifecycle events, while token accounting remains a future backend-specific capability.
