# ADR-0003: Control and identity authorization

Status: Accepted for localhost development only.

Client identities are self-asserted. Any local process that can reach ws://127.0.0.1:8765 can register and send pause, resume, or stop.

Mitigations: loopback bind only; cross-origin handshakes refused; control accepted only from browser clients; system tag accepted only from agents.

Before any non-loopback bind, complete the items in SECURITY.md.
