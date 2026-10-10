"""Agent-to-agent traffic is shown to browsers, never to agents."""

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
    return got


def _feed(frames: list[dict]) -> list[dict]:
    return [f for f in frames if f.get("action") == "agent_feed"]


def test_feed_shows_agent_traffic_to_browsers_only() -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18771)
        instance = await websockets.serve(server.handler, "127.0.0.1", 18771)
        try:
            uri = "ws://127.0.0.1:18771"
            async with (
                websockets.connect(uri) as human,
                websockets.connect(uri) as aegis,
                websockets.connect(uri) as vigil,
            ):
                await human.send(
                    json.dumps({"version": 1, "action": "register", "username": "Thomas"})
                )
                await aegis.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "register",
                            "agent_id": "Aegis-Worker",
                            "capabilities": [],
                        }
                    )
                )
                await vigil.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "register",
                            "agent_id": "Vigil-Worker",
                            "capabilities": [],
                        }
                    )
                )
                await asyncio.sleep(0.3)
                for ws in (human, aegis, vigil):
                    await _frames(ws, 0.3)

                # Agent to agent direct message, and an agent group message
                await aegis.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "direct_message",
                            "recipient": "Vigil-Worker",
                            "message": "why?",
                        }
                    )
                )
                await aegis.send(
                    json.dumps({"version": 1, "action": "broadcast", "message": "group note"})
                )
                # Agent to human direct message: delivered once, never copied to the feed
                await aegis.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "direct_message",
                            "recipient": "Thomas",
                            "message": "to you",
                        }
                    )
                )
                # Human direct message to an agent: not agent traffic
                await human.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "direct_message",
                            "recipient": "Aegis-Worker",
                            "message": "hi",
                        }
                    )
                )

                human_frames = await _frames(human, 1.0)
                vigil_frames = await _frames(vigil, 0.5)
                aegis_frames = await _frames(aegis, 0.5)

                # Group messages already reach every browser, so only direct messages are copied.
                kinds = sorted((f["kind"], f["sender"]) for f in _feed(human_frames))
                assert kinds == [("direct", "Aegis-Worker")], kinds
                direct = next(f for f in _feed(human_frames) if f["kind"] == "direct")
                assert direct["recipient"] == "Vigil-Worker" and direct["message"] == "why?"
                assert all(f["sender"] != "Thomas" for f in _feed(human_frames))

                # Agents never receive feed events, so the feed cannot feed a loop
                assert _feed(vigil_frames) == []
                assert _feed(aegis_frames) == []

                # A browser that joins later sees the recent history
                async with websockets.connect(uri) as late:
                    await late.send(
                        json.dumps({"version": 1, "action": "register", "username": "Late"})
                    )
                    replay = _feed(await _frames(late, 1.0))
                    assert [f["kind"] for f in replay] == ["direct"], replay
                    assert all(f.get("replay") is True for f in replay), replay
        finally:
            instance.close()
            await instance.wait_closed()

    asyncio.run(scenario())
