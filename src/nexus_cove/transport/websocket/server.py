"""WebSocket transport for NEXUS COVE (protocol version 1 only)."""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Any

import websockets

from nexus_cove.observability.chatlog import ChatLog, chat_log_path

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1
# Messages from these sender kinds are agent-to-agent traffic and go to the public feed.
AGENT_SENDER_KINDS = frozenset({"agent", "manager"})
AGENT_MESSAGE_INTERVAL_SECONDS = 20.0
FEED_HISTORY_SIZE = 200
MANAGER_ID = "Nexus-Manager"
# None: non-browser clients (no Origin header). "null": file:// pages.
ALLOWED_ORIGINS: tuple[str | None, ...] = (None, "null")


@dataclass(slots=True)
class Client:
    websocket: Any
    identity: str
    kind: str
    capabilities: frozenset[str]
    paused: bool = False


class CoveWebSocketServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.clients: dict[str, Client] = {}
        self.connected_users: dict[str, str] = {}  # identity -> kind
        self._feed: deque[dict] = deque(maxlen=FEED_HISTORY_SIZE)
        self._last_agent_message_at: float | None = None
        self._stop_event = asyncio.Event()
        self._chatlog = ChatLog(chat_log_path())

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    async def register(self, websocket: Any) -> None:
        """Give a new connection a temporary identity until it registers."""
        identity = f"user_{id(websocket)}"
        kind = "html_client"
        client = Client(websocket, identity, kind, frozenset(["basic_messaging"]))
        self.clients[identity] = client
        self.connected_users[identity] = kind
        logger.info("Client connected: %s", identity)

        await self._send(websocket, {"action": "registered", "identity": identity, "kind": kind})
        await self._broadcast_user_list()

    async def unregister(self, websocket: Any) -> None:
        identity = self._identity_of(websocket)
        if identity is None:
            return
        client = self.clients.pop(identity)
        self.connected_users.pop(identity, None)
        logger.info("Client disconnected: %s (%s)", identity, client.kind)
        await self._broadcast_user_list()

    async def handler(self, websocket: Any) -> None:
        """Entry point used by websockets.serve (single-argument signature)."""
        await self._handle_client(websocket)

    async def _handle_client(self, websocket: Any) -> None:
        await self.register(websocket)
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception:
            logger.exception("Unhandled error in client handler")
        finally:
            await self.unregister(websocket)

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------
    async def _handle_message(self, websocket: Any, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON payload")
            return

        if not isinstance(data, dict) or data.get("version") != PROTOCOL_VERSION:
            await self._send_error(
                websocket, f"Unsupported or missing protocol version; expected {PROTOCOL_VERSION}"
            )
            return

        action = data.get("action")
        handlers = {
            "register": self._on_register,
            "broadcast": self._on_broadcast,
            "direct_message": self._on_direct_message,
            "control": self._on_control,
            "presence": self._on_presence,
            "task_assign": self._on_task_assign,
            "task_result": self._on_task_result,
        }
        if action == "log_request":
            await self._on_log_request(websocket)
        elif action == "ping":
            await self._send(websocket, {"action": "pong"})
        elif action in handlers:
            await handlers[action](websocket, data)
        else:
            await self._send_error(websocket, f"Unknown action: {action!r}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    async def _on_register(self, websocket: Any, data: dict) -> None:
        # Agents (workers, manager) register with agent_id; browser clients use username.
        agent_id = data.get("agent_id")
        requested = agent_id or data.get("username")
        identity = str(requested).strip() if requested else ""
        if not identity:
            identity = f"user_{id(websocket)}"
        is_agent = bool(agent_id)

        existing = self.clients.get(identity)
        if existing is not None and existing.websocket is not websocket:
            try:
                is_open = existing.websocket.state.name == "OPEN"
            except AttributeError:
                is_open = True  # conservative: assume alive if state isn't readable
            if is_open:
                await self._send_error(websocket, f"Identity '{identity}' is already in use")
                return
            # Dead socket still occupies the slot; evict it. The old _handle_client
            # finally block will call unregister(), which is a no-op once evicted.
            logger.warning("Evicting dead registration for %s", identity)
            self.clients.pop(identity, None)
            self.connected_users.pop(identity, None)

        capabilities = frozenset(str(c) for c in (data.get("capabilities") or []))
        if identity == MANAGER_ID:
            kind = "manager"
        elif is_agent:
            kind = "agent"
        else:
            kind = "html_client"

        previous = self._identity_of(websocket)
        if previous is not None:
            self.clients.pop(previous, None)
            self.connected_users.pop(previous, None)

        client = Client(websocket, identity, kind, capabilities)
        self.clients[identity] = client
        self.connected_users[identity] = kind
        logger.info("Registered %s as %s", identity, kind)

        await self._send(websocket, {"action": "registered", "identity": identity, "kind": kind})
        if kind == "html_client":
            for event in list(self._feed):
                await self._send(websocket, {"action": "agent_feed", **event, "replay": True})

        if identity == MANAGER_ID:
            # Manager (re)connected: replay every agent that is already online.
            for other in list(self.clients.values()):
                if other.kind == "agent" and other.identity != MANAGER_ID:
                    await self._send_agent_register(websocket, other)
        elif is_agent:
            manager = self.clients.get(MANAGER_ID)
            if manager is not None:
                await self._send_agent_register(manager.websocket, client)
            else:
                logger.warning("Agent %s registered but manager is not connected", identity)

        await self._broadcast_user_list()

    async def _on_broadcast(self, websocket: Any, data: dict) -> None:
        sender = self._identity_of(websocket)
        if sender is None:
            await self._send_error(websocket, "Connection is not registered")
            return
        sender_kind = self.clients[sender].kind
        text = data.get("message", "")
        self._chatlog.append("group", sender, sender_kind, None, text)
        kind = "system" if data.get("kind") == "system" and sender_kind == "agent" else "chat"
        await self._send_to_all(
            {
                "action": "broadcast",
                "sender": sender,
                "sender_kind": sender_kind,
                "message": text,
                "kind": kind,
            }
        )

    async def _publish_feed(self, event: dict) -> None:
        """Record an agent-to-agent message and show it to every browser client.

        Only html_client connections receive feed events. Agents never do, so the
        feed cannot start or extend an agent conversation.
        """
        stamped = {"at": datetime.now().isoformat(timespec="seconds"), **event}
        self._feed.append(stamped)
        for client in list(self.clients.values()):
            if client.kind == "html_client":
                await self._send(client.websocket, {"action": "agent_feed", **stamped})

    async def _on_log_request(self, websocket: Any) -> None:
        sender = self._identity_of(websocket)
        if sender is None or self.clients[sender].kind != "html_client":
            await self._send_error(websocket, "Only a browser client may request the chat log")
            return
        await self._send(websocket, {"action": "chat_log", "entries": self._chatlog.read()})

    async def _on_presence(self, websocket: Any, data: dict) -> None:
        """An agent reports whether it is paused, so the page can show its status."""
        sender = self._identity_of(websocket)
        if sender is None:
            await self._send_error(websocket, "Connection is not registered")
            return
        client = self.clients[sender]
        if client.kind != "agent":
            await self._send_error(websocket, "Only agents report presence")
            return
        client.paused = bool(data.get("paused"))
        await self._broadcast_user_list()

    async def _on_control(self, websocket: Any, data: dict) -> None:
        """Forward a pause or resume command from a human client to agents."""
        sender = self._identity_of(websocket)
        if sender is None:
            await self._send_error(websocket, "Connection is not registered")
            return
        sender_kind = self.clients[sender].kind
        if sender_kind != "html_client":
            await self._send_error(websocket, "Only a human client may pause or resume agents")
            return
        command = data.get("command")
        if command not in ("pause", "resume", "stop"):
            await self._send_error(websocket, f"Unknown control command: {command!r}")
            return
        target = data.get("target")
        if command == "stop" and target != "all":
            await self._send_error(
                websocket, "stop applies to the whole network: target must be all"
            )
            return
        if target == "all":
            # stop reaches the manager too; pause and resume reach agents only.
            kinds = {"agent", "manager"} if command == "stop" else {"agent"}
            recipients = [c for c in self.clients.values() if c.kind in kinds]
        else:
            client = self.clients.get(target) if isinstance(target, str) else None
            if client is None or client.kind != "agent":
                await self._send_error(websocket, f"{target!r} is not a connected agent")
                return
            recipients = [client]
        if not recipients:
            await self._send_error(websocket, "No agents are connected")
            return
        for client in recipients:
            await self._send(
                client.websocket,
                {
                    "action": "control",
                    "command": command,
                    "sender": sender,
                    "sender_kind": sender_kind,
                },
            )
        if command == "stop":
            # Give the forwarded frames a moment to leave, then close the server.
            asyncio.get_running_loop().call_later(0.5, self._stop_event.set)

    async def _on_direct_message(self, websocket: Any, data: dict) -> None:
        sender = self._identity_of(websocket)
        if sender is None:
            await self._send_error(websocket, "Connection is not registered")
            return
        recipient = data.get("recipient")
        target = self.clients.get(recipient) if recipient else None
        if target is None:
            await self._send_error(websocket, f"User '{recipient}' not found")
            return
        sender_kind = self.clients[sender].kind
        is_agent_conversation = (
            sender_kind in AGENT_SENDER_KINDS and target.kind in AGENT_SENDER_KINDS
        )
        if is_agent_conversation:
            now = monotonic()
            if self._last_agent_message_at is not None:
                elapsed = now - self._last_agent_message_at
                if elapsed < AGENT_MESSAGE_INTERVAL_SECONDS:
                    retry_after = AGENT_MESSAGE_INTERVAL_SECONDS - elapsed
                    await self._send_error(
                        websocket,
                        "Agent-to-agent messages must be at least 20 seconds apart; "
                        f"retry in {retry_after:.2f} seconds",
                    )
                    return
            self._last_agent_message_at = now
        text = data.get("message", "")
        await self._send(
            target.websocket,
            {
                "action": "direct_message",
                "sender": sender,
                "sender_kind": sender_kind,
                "message": text,
            },
        )
        self._chatlog.append("direct", sender, sender_kind, recipient, text)
        # Copy to the feed only when an agent writes to another agent. A message from an agent
        # to a human is already delivered to that human and must not appear twice.
        if sender_kind in AGENT_SENDER_KINDS and target.kind in AGENT_SENDER_KINDS:
            await self._publish_feed(
                {"kind": "direct", "sender": sender, "recipient": recipient, "message": text}
            )

    async def _on_task_assign(self, websocket: Any, data: dict) -> None:
        sender = self._identity_of(websocket)
        if sender != MANAGER_ID:
            await self._send_error(websocket, "Only the manager may assign tasks")
            return
        recipient = data.get("recipient")
        target = self.clients.get(recipient) if recipient else None
        if target is None or target.kind != "agent":
            await self._send_error(websocket, f"Agent '{recipient}' is not connected")
            return
        await self._send(target.websocket, data)

    async def _on_task_result(self, websocket: Any, data: dict) -> None:
        sender = self._identity_of(websocket)
        if sender is None:
            await self._send_error(websocket, "Connection is not registered")
            return
        manager = self.clients.get(MANAGER_ID)
        if manager is None:
            await self._send_error(websocket, "Manager is not connected; result not delivered")
            return
        await self._send(manager.websocket, data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _identity_of(self, websocket: Any) -> str | None:
        for client in self.clients.values():
            if client.websocket is websocket:
                return client.identity
        return None

    async def _send(self, websocket: Any, payload: dict) -> None:
        body = {"version": PROTOCOL_VERSION, **payload}
        try:
            await websocket.send(json.dumps(body))
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Send skipped: connection already closed")

    async def _send_error(self, websocket: Any, text: str) -> None:
        await self._send(websocket, {"action": "error", "error": text})

    async def _send_agent_register(self, websocket: Any, agent: Client) -> None:
        await self._send(
            websocket,
            {
                "action": "agent_register",
                "agent_id": agent.identity,
                "capabilities": sorted(agent.capabilities),
            },
        )

    async def _send_to_all(self, payload: dict) -> None:
        if not self.clients:
            return
        body = json.dumps({"version": PROTOCOL_VERSION, **payload})
        await asyncio.gather(
            *[client.websocket.send(body) for client in list(self.clients.values())],
            return_exceptions=True,
        )

    @staticmethod
    def _is_temporary_identity(identity: str) -> bool:
        return identity.startswith("user_")

    async def _broadcast_user_list(self) -> None:
        if not self.clients:
            return
        visible_users = [
            (identity, kind)
            for identity, kind in self.connected_users.items()
            if not self._is_temporary_identity(identity)
        ]
        await self._send_to_all(
            {
                "action": "user_list",
                "users": [
                    {
                        "identity": identity,
                        "kind": kind,
                        "paused": (
                            bool(self.clients[identity].paused)
                            if identity in self.clients
                            else False
                        ),
                    }
                    for identity, kind in visible_users
                ],
            }
        )

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        logger.info("Starting WebSocket server on ws://%s:%s", self.host, self.port)
        async with websockets.serve(
            self.handler, self.host, self.port, origins=list(ALLOWED_ORIGINS)
        ):
            await self._stop_event.wait()  # returns when a stop command arrives

    async def stop(self) -> None:
        logger.info("Stopping WebSocket server")
        if self.clients:
            await asyncio.gather(
                *[client.websocket.close() for client in self.clients.values()],
                return_exceptions=True,
            )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NEXUS COVE WebSocket Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        logging.getLogger(__name__).warning(
            "Binding to %s exposes an unauthenticated endpoint; "
            "use 127.0.0.1 for local development (see SECURITY.md)",
            args.host,
        )
    asyncio.run(CoveWebSocketServer(args.host, args.port).start())


if __name__ == "__main__":
    main()

