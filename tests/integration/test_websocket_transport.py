import asyncio

import websockets

from nexus_cove.core.protocols import decode_message, encode_message
from nexus_cove.transport.websocket.server import CoveWebSocketServer


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
