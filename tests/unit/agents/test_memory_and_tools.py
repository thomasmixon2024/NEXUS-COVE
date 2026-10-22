from pathlib import Path

import pytest

from nexus_cove.agents.memory import AgentMemory
from nexus_cove.agents.tools import CodeAnalyzer, PatternFinder, toolkit_for


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


def test_code_analyzer_returns_none_without_trigger(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    assert analyzer.run("hello there") is None
    assert analyzer.run("just a normal message") is None


def test_code_analyzer_parses_clean_code(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    code = """
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""
    result = analyzer.run(f"debug this:\n```python\n{code}\n```")
    assert result is not None
    assert "Code parsed cleanly" in result
    assert "2 function(s)" in result
    assert "1 class(es)" in result
    assert "No unused imports or obvious undefined names detected" in result


def test_code_analyzer_detects_syntax_error(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    code = """
def broken(
    return 1
"""
    result = analyzer.run(f"debug this:\n```python\n{code}\n```")
    assert result is not None
    assert result.startswith("SyntaxError at line")
    assert "col" in result


def test_code_analyzer_detects_unused_import(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    code = """
import os
import sys

def hello():
    print("hello")
"""
    result = analyzer.run(f"debug this:\n```python\n{code}\n```")
    assert result is not None
    assert "Unused imports" in result
    # Either os or sys should be reported as unused
    assert "os" in result or "sys" in result


def test_code_analyzer_detects_undefined_name(tmp_path: Path) -> None:
    analyzer = CodeAnalyzer()
    code = """
def foo():
    return x + y
"""
    result = analyzer.run(f"debug this:\n```python\n{code}\n```")
    assert result is not None
    assert "Potentially undefined names" in result
    assert "x" in result
    assert "y" in result


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
    assert [type(t).__name__ for t in aegis] == ["CodeAnalyzer"]
    assert [type(t).__name__ for t in vigil] == ["PatternFinder"]
    assert toolkit_for("Some-Other-Agent", memory) == ()
