"""Every delivered message is written once; only browsers can read the log back."""

import asyncio
import json
from pathlib import Path

import pytest
import websockets

from nexus_cove.observability.chatlog import ChatLog, chat_log_path
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


def test_chat_log_appends_one_line_per_message(tmp_path: Path) -> None:
    log = ChatLog(tmp_path / "nexus_chat.jsonl")
    log.append("group", "Thomas", "html_client", None, "hello everyone")
    log.append("direct", "Aegis-Worker", "agent", "Vigil-Worker", "why?")
    lines = (tmp_path / "nexus_chat.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["recipient"] == "Vigil-Worker"
    assert [e["message"] for e in log.read()] == ["hello everyone", "why?"]


def test_chat_log_path_follows_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEXUS_COVE_LOG_DIR", str(tmp_path))
    assert chat_log_path() == tmp_path / "nexus_chat.jsonl"


def test_server_logs_each_message_once_and_serves_it_to_browsers_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEXUS_COVE_LOG_DIR", str(tmp_path))

    async def scenario() -> None:
        server = CoveWebSocketServer(port=18775)
        serving = asyncio.create_task(server.start())
        await asyncio.sleep(0.3)
        uri = "ws://127.0.0.1:18775"
        async with (
            websockets.connect(uri) as human,
            websockets.connect(uri) as aegis,
            websockets.connect(uri) as vigil,
        ):
            await human.send(json.dumps({"version": 1, "action": "register", "username": "Thomas"}))
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
                await _frames(ws, 0.2)

            await human.send(
                json.dumps({"version": 1, "action": "broadcast", "message": "group hi"})
            )
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
            await asyncio.sleep(0.3)

            # A browser can read the log; an agent cannot.
            await human.send(json.dumps({"version": 1, "action": "log_request"}))
            logs = [f for f in await _frames(human, 0.5) if f.get("action") == "chat_log"]
            assert logs, "browser must receive the chat log"
            texts = [(e["kind"], e["message"]) for e in logs[0]["entries"]]
            assert texts == [("group", "group hi"), ("direct", "why?")], texts

            await aegis.send(json.dumps({"version": 1, "action": "log_request"}))
            refused = [f for f in await _frames(aegis, 0.5) if f.get("action") == "error"]
            assert refused and not [f for f in refused if f.get("action") == "chat_log"]

        serving.cancel()
        try:
            await serving
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())
    lines = (tmp_path / "nexus_chat.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "each message is written once, not once per recipient"
