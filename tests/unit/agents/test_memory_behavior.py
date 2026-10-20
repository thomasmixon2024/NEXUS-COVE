import logging
from pathlib import Path

import pytest

import nexus_cove.agents.memory as memory_module
from nexus_cove.agents.memory import MAX_HIGHLIGHTS, AgentMemory


def test_agent_name_defaults_to_the_file_name(tmp_path: Path) -> None:
    assert AgentMemory(tmp_path / "Aegis-Worker.jsonl").agent_name == "Aegis-Worker"


def test_agents_sharing_a_directory_keep_separate_state(tmp_path: Path) -> None:
    aegis = AgentMemory(tmp_path / "Aegis-Worker.jsonl")
    vigil = AgentMemory(tmp_path / "Vigil-Worker.jsonl")
    aegis.append("received", "Thomas", "- aegis only note")
    vigil.append("received", "Thomas", "- vigil only note")
    assert aegis.get_highlights() == ["- aegis only note"]
    assert vigil.get_highlights() == ["- vigil only note"]
    assert aegis.get_latest_session_checkpoint()["agent_name"] == "Aegis-Worker"
    assert vigil.get_latest_session_checkpoint()["agent_name"] == "Vigil-Worker"


def test_unsafe_agent_name_cannot_leave_the_memory_directory(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl", agent_name="../../evil/name")
    memory.append("received", "x", "- note")
    created = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert created and all(tmp_path in p.parents for p in created)


@pytest.mark.parametrize(
    "line",
    ["- a bullet", "* another", "1. numbered", "> quoted", "Decision: use sqlite",
     "we fixed the bug", "Error: timeout", "this is critical", "TODO write tests"],
)
def test_lines_that_look_important_are_kept(tmp_path: Path, line: str) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    memory.append("received", "x", f"chatter\n{line}\nmore chatter")
    assert memory.get_highlights() == [line]


@pytest.mark.parametrize(
    "line",
    [
        "a prefix and a suffix",
        "plain chatter",
        "terrorism is unrelated",
    ],
)
def test_keywords_inside_other_words_are_not_highlights(tmp_path: Path, line: str) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    memory.append("received", "x", line)
    assert memory.get_highlights() == []


def test_highlights_survive_reopening_and_are_capped(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    memory = AgentMemory(path)
    for i in range(MAX_HIGHLIGHTS + 7):
        memory.append("received", "x", f"- note {i}")
    reopened = AgentMemory(path).get_highlights()
    assert len(reopened) == MAX_HIGHLIGHTS
    assert reopened[-1] == f"- note {MAX_HIGHLIGHTS + 6}"
    assert reopened[0] == "- note 7"


def test_snapshot_is_written_once_per_interval_not_per_message(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    memory.checkpoint_every = 5
    for i in range(12):
        memory.append("received", "x", f"msg {i}")
    snapshots = sorted((tmp_path / "checkpoints").glob("m_checkpoint_*.json"))
    assert len(snapshots) == 2  # after message 5 and message 10
    latest = memory.load_latest_checkpoint()
    assert latest is not None and latest["message_count"] == 10


def test_append_does_not_rescan_the_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    calls = []
    real = memory_module.iter_jsonl
    monkeypatch.setattr(memory_module, "iter_jsonl", lambda p: calls.append(p) or real(p))
    for i in range(25):
        memory.append("received", "x", f"msg {i}")
    assert calls == []


def test_count_is_correct_when_the_log_already_has_messages(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    first = AgentMemory(path)
    for i in range(3):
        first.append("received", "x", f"msg {i}")
    second = AgentMemory(path)
    second.append("sent", "x", "msg 3")
    assert second.save_checkpoint("t") and second.load_latest_checkpoint()["message_count"] == 4


def test_unreadable_highlight_file_is_ignored_with_a_warning(
        tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "m.highlights.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        memory = AgentMemory(tmp_path / "m.jsonl")
    assert memory.get_highlights() == []
    assert "unreadable memory file" in caplog.text


def test_session_journal_is_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_module, "MAX_SESSION_CHECKPOINTS", 3)
    for _ in range(6):
        AgentMemory(tmp_path / "m.jsonl")
    assert len(AgentMemory(tmp_path / "m.jsonl").get_session_checkpoint_history(limit=50)) == 3


def test_startup_flush_reports_highlights_and_deletes_nothing(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    memory.append("received", "x", "- keep me")
    report = memory.startup_flush_with_highlight_retention()
    assert report["highlights_preserved"] == ["- keep me"]
    assert report["message_count_before_flush"] == 1
    assert [e["text"] for e in memory.entries()] == ["- keep me"]
