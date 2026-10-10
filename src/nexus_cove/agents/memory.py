"""Per-agent memory: a log of what an agent heard and what it said.

Each agent appends one JSON line per message to its own file. Entries are
never edited. The worker puts the most recent entries into each prompt, so
an agent can refer back to earlier conversation.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

DIRECTIONS = frozenset({"sent", "received"})


class AgentMemory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, direction: str, peer: str, text: str) -> None:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be 'sent' or 'received', got {direction!r}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "direction": direction,
            "peer": peer,
            "text": text,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def recent(self, limit: int) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as handle:
            tail = deque((line for line in handle if line.strip()), maxlen=limit)
        return [json.loads(line) for line in tail]
