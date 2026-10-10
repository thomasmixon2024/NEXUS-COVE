import asyncio
import json
from pathlib import Path

import pytest

from nexus_cove.agents.backends.deterministic_backend import DeterministicTestBackend
from nexus_cove.agents.knowledge import KnowledgeStore, knowledge_folder, parse_shares
from nexus_cove.agents.memory import AgentMemory
from nexus_cove.agents.worker import Worker
from nexus_cove.core.models import Agent, AgentStatus


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, text: str) -> None:
        self.sent.append(json.loads(text))


class RecordingReplier:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def areply(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


def _worker(
    tmp_path: Path, replier, knowledge: KnowledgeStore, name: str = "Aegis-Worker"
) -> Worker:
    return Worker(
        Agent(name, frozenset(), AgentStatus.OFFLINE),
        DeterministicTestBackend(),
        "ws://127.0.0.1:1",
        replier=replier,
        memory=AgentMemory(tmp_path / "memory.jsonl"),
        knowledge=knowledge,
    )


def _store(tmp_path: Path, agent: str, items: dict[str, str]) -> KnowledgeStore:
    folder = tmp_path / "knowledge" / agent
    folder.mkdir(parents=True)
    for title, body in items.items():
        (folder / f"{title}.md").write_text(body, encoding="utf-8")
    return KnowledgeStore(folder)


def test_each_agent_sees_only_its_own_items(tmp_path: Path) -> None:
    aegis = _store(tmp_path, "Aegis-Worker", {"tunnels": "Arches spread load."})
    vigil = _store(tmp_path, "Vigil-Worker", {"bees": "They dance."})
    assert set(aegis.items()) == {"tunnels"}
    assert set(vigil.items()) == {"bees"}
    assert vigil.find("tunnels") is None


def test_missing_folder_means_no_knowledge(tmp_path: Path) -> None:
    assert KnowledgeStore(tmp_path / "nowhere").items() == {}


def test_invalid_agent_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        knowledge_folder("../escape")


def test_parse_shares_strips_share_lines_and_keeps_the_rest() -> None:
    visible, titles = parse_shares("Arches spread load.\nSHARE: tunnels\nWhy do you ask?")
    assert visible == "Arches spread load.\nWhy do you ask?"
    assert titles == ["tunnels"]


def test_no_share_line_means_nothing_is_shared(tmp_path: Path) -> None:
    store = _store(tmp_path, "Aegis-Worker", {"tunnels": "Arches spread load."})
    replier = RecordingReplier("A reply with no sharing in it.")
    worker = _worker(tmp_path, replier, store)
    ws = FakeWS()
    asyncio.run(worker._answer_direct(ws, "Vigil-Worker", "what do you know?"))
    assert [m["message"] for m in ws.sent] == ["A reply with no sharing in it."]


def test_chosen_item_is_sent_to_the_peer_and_the_share_line_is_hidden(tmp_path: Path) -> None:
    store = _store(tmp_path, "Aegis-Worker", {"tunnels": "Arches spread load."})
    replier = RecordingReplier("Here is something I know.\nSHARE: tunnels")
    worker = _worker(tmp_path, replier, store)
    ws = FakeWS()
    asyncio.run(worker._answer_direct(ws, "Vigil-Worker", "tell me about tunnels"))
    messages = [m["message"] for m in ws.sent]
    assert messages[0] == "Here is something I know."
    assert messages[1].startswith("[shared knowledge: tunnels]\nArches spread load.")
    assert all("SHARE:" not in m for m in messages)
    assert all(m["recipient"] == "Vigil-Worker" for m in ws.sent)


def test_prompt_contains_only_this_agents_knowledge_and_the_sharing_rule(tmp_path: Path) -> None:
    store = _store(tmp_path, "Aegis-Worker", {"tunnels": "Arches spread load."})
    replier = RecordingReplier("ok")
    worker = _worker(tmp_path, replier, store)
    asyncio.run(worker._answer_direct(FakeWS(), "Thomas", "hello"))
    prompt = replier.prompts[0]
    assert "Arches spread load." in prompt
    assert "SHARE: <title>" in prompt


def test_naming_an_item_it_does_not_hold_shares_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path, "Aegis-Worker", {"tunnels": "Arches spread load."})
    worker = _worker(tmp_path, RecordingReplier("Sharing a secret.\nSHARE: secret"), store)
    ws = FakeWS()
    asyncio.run(worker._answer_direct(ws, "Vigil-Worker", "hi"))
    assert [m["message"] for m in ws.sent] == ["Sharing a secret."]
