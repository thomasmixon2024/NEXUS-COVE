import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import websockets

from nexus_cove.core.protocols import decode_message, encode_message
from nexus_cove.transport.websocket.server import Client, CoveWebSocketServer


def test_websocket_registration_and_ping() -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18765)
        server_instance = await websockets.serve(server.handler, "127.0.0.1", 18765)
        try:
            async with websockets.connect("ws://127.0.0.1:18765") as ws:
                await ws.send(
                    encode_message("register", agent_id="TestAgent", capabilities=["general"])
                )
                registered = decode_message(await ws.recv())
                assert registered["action"] == "registered"
                await ws.send(encode_message("ping"))
                # Connection and registration broadcasts may arrive before the pong.
                seen = set()
                while True:
                    reply = decode_message(await ws.recv())
                    seen.add(reply["action"])
                    if reply["action"] == "pong":
                        break
                    assert reply["action"] in {"registered", "user_list"}, reply
                assert "pong" in seen
        finally:
            server_instance.close()
            await server_instance.wait_closed()

    asyncio.run(scenario())


def test_stale_dead_registration_is_evicted() -> None:
    """Reconnecting with the same agent_id succeeds when the prior connection is dead."""

    async def scenario() -> None:
        server = CoveWebSocketServer(port=18766)
        srv = await websockets.serve(server.handler, "127.0.0.1", 18766)
        try:
            dead_ws = MagicMock()
            dead_ws.state.name = "CLOSED"
            dead_ws.send = AsyncMock(side_effect=Exception("connection closed"))
            server.clients["Reconnector"] = Client(
                dead_ws, "Reconnector", "agent", frozenset(["general"])
            )
            server.connected_users["Reconnector"] = "agent"

            async with websockets.connect("ws://127.0.0.1:18766") as ws:
                await ws.recv()  # discard initial temp-registered message
                await ws.send(
                    encode_message("register", agent_id="Reconnector", capabilities=["general"])
                )
                for _ in range(5):
                    msg = decode_message(await asyncio.wait_for(ws.recv(), timeout=1.0))
                    if msg["action"] == "registered":
                        assert msg["identity"] == "Reconnector"
                        return
                    assert msg["action"] != "error", f"Registration rejected: {msg.get('error')}"
                raise AssertionError("No registered message received")
        finally:
            srv.close()
            await srv.wait_closed()

    asyncio.run(scenario())


def test_temp_html_id_is_filtered_from_user_list() -> None:
    """Temporary user_... identities should not keep triggering agent chatter."""

    async def scenario() -> None:
        server = CoveWebSocketServer(port=18767)
        ws_a = MagicMock()
        ws_a.send = AsyncMock()
        ws_b = MagicMock()
        ws_b.send = AsyncMock()
        server.clients["user_ghost"] = Client(
            ws_a, "user_ghost", "html_client", frozenset(["basic_messaging"])
        )
        server.clients["Alice"] = Client(
            ws_b, "Alice", "html_client", frozenset(["basic_messaging"])
        )
        server.connected_users["user_ghost"] = "html_client"
        server.connected_users["Alice"] = "html_client"

        await server._broadcast_user_list()

        payload = json.loads(ws_a.send.await_args.args[0])
        identities = [user["identity"] for user in payload["users"]]
        assert identities == ["Alice"]

    asyncio.run(scenario())
