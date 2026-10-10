from pathlib import Path

import pytest

from nexus_cove.agents.memory import AgentMemory
from nexus_cove.agents.tools import GeologyAnalyzer, PatternFinder, toolkit_for

HEADER = "material,property,value,unit,source\n"


def test_memory_keeps_order_and_survives_reopening(tmp_path: Path) -> None:
    path = tmp_path / "memory" / "Aegis-Worker.jsonl"
    AgentMemory(path).append("received", "Thomas", "first")
    AgentMemory(path).append("sent", "Thomas", "second")
    reopened = AgentMemory(path)
    assert [e["text"] for e in reopened.entries()] == ["first", "second"]
    assert [e["text"] for e in reopened.recent(1)] == ["second"]


def test_memory_rejects_unknown_direction(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        AgentMemory(tmp_path / "m.jsonl").append("overheard", "x", "y")


def test_geology_is_silent_without_a_reference_file(tmp_path: Path) -> None:
    assert GeologyAnalyzer(tmp_path / "missing.csv").run("tell me about granite") is None


def test_geology_is_silent_with_header_only(tmp_path: Path) -> None:
    csv_path = tmp_path / "geology.csv"
    csv_path.write_text(HEADER, encoding="utf-8")
    assert GeologyAnalyzer(csv_path).run("tell me about granite") is None


def test_geology_reports_only_rows_for_materials_named(tmp_path: Path) -> None:
    csv_path = tmp_path / "geology.csv"
    csv_path.write_text(
        HEADER
        + "granite,compressive strength,170,MPa,Test source\n"
        + "basalt,density,2900,kg/m3,Other source\n",
        encoding="utf-8",
    )
    result = GeologyAnalyzer(csv_path).run("Is granite strong enough for a tunnel?")
    assert result is not None
    assert "granite: compressive strength = 170 MPa (source: Test source)" in result
    assert "basalt" not in result
    assert GeologyAnalyzer(csv_path).run("nothing relevant here") is None


def test_geology_rejects_a_file_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "geology.csv"
    csv_path.write_text("material,value\ngranite,170\n", encoding="utf-8")
    with pytest.raises(ValueError):
        GeologyAnalyzer(csv_path).run("granite")


def test_pattern_finder_waits_for_enough_messages(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "v.jsonl")
    memory.append("received", "Thomas", "why do bees dance?")
    result = PatternFinder(memory).run("what patterns do you see?")
    assert result is not None and "needs 5" in result


def test_pattern_finder_counts_words_and_questions_heard(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "v.jsonl")
    for text in [
        "why do bees dance?",
        "bees dance to share flowers?",
        "why do stories repeat?",
        "stories repeat shapes",
        "music repeats patterns",
    ]:
        memory.append("received", "Thomas", text)
    memory.append("sent", "Thomas", "sent text is not counted")
    result = PatternFinder(memory).run("what is the most common pattern?")
    assert result is not None
    assert "from 5 messages heard" in result
    # "repeat" appears twice ("repeats" is a different word); three of five messages are questions.
    assert "repeat (2)" in result
    assert "Questions heard: 3." in result


def test_pattern_finder_only_runs_on_its_trigger_words(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "v.jsonl")
    assert PatternFinder(memory).run("hello there") is None


def test_each_agent_gets_only_its_tool(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    aegis = toolkit_for("Aegis-Worker", memory)
    vigil = toolkit_for("Vigil-Worker", memory)
    assert [type(t).__name__ for t in aegis] == ["GeologyAnalyzer"]
    assert [type(t).__name__ for t in vigil] == ["PatternFinder"]
    assert toolkit_for("Some-Other-Agent", memory) == ()
