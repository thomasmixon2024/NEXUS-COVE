"""A human's stop command reaches the agents and shuts the server down."""

import asyncio
import json

import websockets

from nexus_cove.transport.websocket.server import CoveWebSocketServer


async def _frames(ws, seconds: float) -> list[dict]:
    got: list[dict] = []
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    while loop.time() < end:
        try:
            got.append(json.loads(await asyncio.wait_for(ws.recv(), 0.2)))
        except TimeoutError:
            pass
        except websockets.exceptions.ConnectionClosed:
            break  # the server closed the connection after the stop
    return got


def test_stop_reaches_agents_and_closes_server() -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18773)
        serving = asyncio.create_task(server.start())
        await asyncio.sleep(0.3)
        uri = "ws://127.0.0.1:18773"
        async with websockets.connect(uri) as human, websockets.connect(uri) as agent:
            await human.send(json.dumps({"version": 1, "action": "register", "username": "Thomas"}))
            await agent.send(
                json.dumps(
                    {
                        "version": 1,
                        "action": "register",
                        "agent_id": "Aegis-Worker",
                        "capabilities": [],
                    }
                )
            )
            await asyncio.sleep(0.3)
            await _frames(human, 0.2)
            await _frames(agent, 0.2)

            # Only a human may stop the network; an agent's attempt is refused.
            await agent.send(
                json.dumps({"version": 1, "action": "control", "target": "all", "command": "stop"})
            )
            refused = [f for f in await _frames(agent, 0.5) if f.get("action") == "error"]
            assert refused, "agents must not be able to stop the network"
            assert not serving.done()

            await human.send(
                json.dumps({"version": 1, "action": "control", "target": "all", "command": "stop"})
            )
            got = [f for f in await _frames(agent, 1.0) if f.get("action") == "control"]
            assert [f["command"] for f in got] == ["stop"], got

        # The server closes itself shortly after forwarding the stop.
        await asyncio.wait_for(serving, timeout=3)

    asyncio.run(scenario())
