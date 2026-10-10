"""A pause must stop a reply that is still being written.

Regression test for: a model reply started before a pause was sent anyway.
"""

import asyncio
import json
from pathlib import Path

import pytest
import websockets

from nexus_cove.agents.backends.deterministic_backend import DeterministicTestBackend
from nexus_cove.agents.pause import DATA_DIR_ENV
from nexus_cove.agents.worker import Worker
from nexus_cove.core.models import Agent, AgentStatus
from nexus_cove.transport.websocket.server import CoveWebSocketServer


class SlowReplier:
    """Stands in for a model that takes two seconds to answer."""

    async def areply(self, user_text: str) -> str:
        await asyncio.sleep(2.0)
        return "a late reply that must never be sent"


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


@pytest.mark.parametrize("port", [18772])
def test_pause_sent_during_a_reply_stops_that_reply(tmp_path: Path, monkeypatch, port: int) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))

    async def scenario() -> None:
        server = CoveWebSocketServer(port=port)
        instance = await websockets.serve(server.handler, "127.0.0.1", port)
        worker = Worker(
            Agent("Aegis-Worker", frozenset(), AgentStatus.OFFLINE),
            DeterministicTestBackend(),
            f"ws://127.0.0.1:{port}",
            replier=SlowReplier(),
        )
        worker_task = asyncio.create_task(worker.run())
        try:
            uri = f"ws://127.0.0.1:{port}"
            async with websockets.connect(uri) as human:
                await human.send(
                    json.dumps({"version": 1, "action": "register", "username": "Thomas"})
                )
                await asyncio.sleep(0.5)  # let the worker register

                await human.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "direct_message",
                            "recipient": "Aegis-Worker",
                            "message": "hello?",
                        }
                    )
                )
                await asyncio.sleep(0.3)  # the worker is now writing its reply
                await human.send(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "control",
                            "target": "Aegis-Worker",
                            "command": "pause",
                        }
                    )
                )
                frames = await _frames(human, 3.0)

            replies = [
                f
                for f in frames
                if f.get("action") == "direct_message" and f.get("sender") == "Aegis-Worker"
            ]
            status = [
                f
                for f in frames
                if f.get("action") == "broadcast" and "is paused" in f.get("message", "")
            ]
            assert replies == [], f"reply sent after pause: {replies}"
            assert status, "pause status line was not posted"
            assert (tmp_path / "paused" / "Aegis-Worker.flag").exists()
        finally:
            worker_task.cancel()
            await asyncio.gather(worker_task, return_exceptions=True)
            instance.close()
            await instance.wait_closed()

    asyncio.run(scenario())
