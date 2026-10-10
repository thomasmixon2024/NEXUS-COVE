"""The server must stamp each forwarded direct message with the sender's kind."""

import asyncio
import json

import websockets

from nexus_cove.transport.websocket.server import CoveWebSocketServer


async def _next_direct_message(ws, timeout: float = 3.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise AssertionError("no direct_message received")
        frame = json.loads(await asyncio.wait_for(ws.recv(), remaining))
        if frame.get("action") == "direct_message":
            return frame


def test_direct_message_carries_sender_kind() -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18770)
        server_instance = await websockets.serve(server.handler, "127.0.0.1", 18770)
        try:
            uri = "ws://127.0.0.1:18770"
            async with websockets.connect(uri) as human, websockets.connect(uri) as agent:
                await human.send(
                    json.dumps({"version": 1, "action": "register", "username": "Thomas"})
                )
                await agent.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "register",
                            "agent_id": "Aegis-Worker",
                            "capabilities": ["general"],
                        }
                    )
                )
                await asyncio.sleep(0.2)
                await agent.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "direct_message",
                            "recipient": "Thomas",
                            "message": "hello mentor",
                        }
                    )
                )
                frame = await _next_direct_message(human)
                assert frame["sender"] == "Aegis-Worker"
                assert frame["sender_kind"] == "agent"
                assert frame["message"] == "hello mentor"
        finally:
            server_instance.close()
            await server_instance.wait_closed()

    asyncio.run(scenario())
