"""Agents report their pause state, and the roster carries it to the page."""

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
            break
    return got


def _latest_roster(frames: list[dict]) -> dict[str, bool]:
    rosters = [f for f in frames if f.get("action") == "user_list"]
    return {u["identity"]: u["paused"] for u in rosters[-1]["users"]}


def test_agent_presence_reaches_the_roster() -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18774)
        instance = await websockets.serve(server.handler, "127.0.0.1", 18774)
        try:
            uri = "ws://127.0.0.1:18774"
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
                            "capabilities": [],
                        }
                    )
                )
                await asyncio.sleep(0.3)
                await _frames(human, 0.3)

                await agent.send(json.dumps({"version": 1, "action": "presence", "paused": True}))
                assert _latest_roster(await _frames(human, 0.5))["Aegis-Worker"] is True

                await agent.send(json.dumps({"version": 1, "action": "presence", "paused": False}))
                assert _latest_roster(await _frames(human, 0.5))["Aegis-Worker"] is False

                # Only agents report presence; a human's attempt is refused.
                await human.send(json.dumps({"version": 1, "action": "presence", "paused": True}))
                refused = [f for f in await _frames(human, 0.5) if f.get("action") == "error"]
                assert refused
        finally:
            instance.close()
            await instance.wait_closed()

    asyncio.run(scenario())
