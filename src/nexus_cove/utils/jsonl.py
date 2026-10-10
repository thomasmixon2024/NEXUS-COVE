"""Stream-oriented JSONL helpers — bounded memory, skip corrupt lines."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield objects from a JSONL file. Corrupt lines are skipped."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    """Return the last ``limit`` valid JSON objects without loading the whole file into a list first."""
    if limit < 1 or not path.is_file():
        return []
    tail: deque[str] = deque(maxlen=limit)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tail.append(line)
    out: list[dict[str, Any]] = []
    for line in tail:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON object as a single line. Creates parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
