from pathlib import Path

import pytest

from nexus_cove.agents.memory import AgentMemory
from nexus_cove.agents.tools import DebugAssistant, DevAssistant, toolkit_for


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


# DebugAssistant tests

def test_debug_assistant_returns_none_for_plain_text(tmp_path: Path) -> None:
    da = DebugAssistant()
    assert da.run("hello there") is None
    assert da.run("just a normal message") is None


def test_debug_assistant_identifies_index_error(tmp_path: Path) -> None:
    da = DebugAssistant()
    text = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    x = lst[5]
IndexError: list index out of range
"""
    result = da.run(text)
    assert result is not None
    assert "IndexError" in result
    assert "list index out of range" in result
    assert "IndexError" in result or "out of range" in result


def test_debug_assistant_identifies_type_error(tmp_path: Path) -> None:
    da = DebugAssistant()
    text = """
Traceback (most recent call last):
  File "test.py", line 5, in <module>
    result = None + 5
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
"""
    result = da.run(text)
    assert result is not None
    assert "TypeError" in result
    assert "NoneType" in result or "int" in result
    assert "Wrong type" in result or "calling something on None" in result


def test_debug_assistant_extracts_last_frame(tmp_path: Path) -> None:
    da = DebugAssistant()
    text = """
Traceback (most recent call last):
  File "a.py", line 1, in <module>
    foo()
  File "b.py", line 5, in foo
    bar()
  File "c.py", line 10, in bar
    raise ValueError: bad value
ValueError: bad value
"""
    result = da.run(text)
    assert result is not None
    assert "ValueError" in result
    assert "bad value" in result
    assert "c.py" in result
    assert "c.py:10" in result
    assert "bar" in result


# DevAssistant tests

def test_dev_assistant_returns_none_for_plain_text(tmp_path: Path) -> None:
    da = DevAssistant()
    assert da.run("hello there") is None
    assert da.run("just a normal message") is None


def test_dev_assistant_finds_unused_imports(tmp_path: Path) -> None:
    da = DevAssistant()
    code = """
```python
import os
import sys

def hello():
    print("hello")
```
"""
    result = da.run(code)
    assert result is not None
    assert "Unused imports" in result
    assert "os" in result
    assert "sys" in result


def test_dev_assistant_reports_missing_docstrings(tmp_path: Path) -> None:
    da = DevAssistant()
    code = """
```python
def foo():
    return 1

class Bar:
    pass
```
"""
    result = da.run(code)
    assert result is not None
    assert "Missing docstrings" in result
    assert "2 of 2 definitions" in result


def test_dev_assistant_handles_syntax_error(tmp_path: Path) -> None:
    da = DevAssistant()
    code = """
```python
def broken(
    return 1
```
"""
    result = da.run(code)
    assert result is not None
    assert "SyntaxError" in result
    assert "Fix the syntax first" in result


def test_dev_assistant_finds_complex_function(tmp_path: Path) -> None:
    da = DevAssistant()
    code = """
```python
def complex_func(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0 and x > 10:
                while i < 10:
                    try:
                        pass
                    except:
                        pass
                    finally:
                        pass
    return x
```
"""
    result = da.run(code)
    assert result is not None
    assert "Complex functions" in result
    assert "complex_func" in result


# toolkit_for tests

def test_toolkit_assigns_debug_to_aegis(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    tools = toolkit_for("Aegis-Worker", memory)
    assert len(tools) == 1
    assert isinstance(tools[0], DebugAssistant)
    assert tools[0].name == "Debug Assistant"


def test_toolkit_assigns_dev_to_vigil(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    tools = toolkit_for("Vigil-Worker", memory)
    assert len(tools) == 1
    assert isinstance(tools[0], DevAssistant)
    assert tools[0].name == "Dev Assistant"


def test_toolkit_returns_empty_for_others(tmp_path: Path) -> None:
    memory = AgentMemory(tmp_path / "m.jsonl")
    assert toolkit_for("Elon-Worker", memory) == ()
    assert toolkit_for("Some-Other-Agent", memory) == ()