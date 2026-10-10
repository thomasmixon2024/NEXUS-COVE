"""Per-agent memory: a log of what an agent heard and what it said.

Each agent appends one JSON line per message to its own file. Entries are
never edited. The worker puts the most recent entries into each prompt, so
an agent can refer back to earlier conversation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from nexus_cove.utils.jsonl import append_jsonl, iter_jsonl, read_jsonl_tail

DIRECTIONS = frozenset({"sent", "received"})


class AgentMemory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, direction: str, peer: str, text: str) -> None:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be 'sent' or 'received', got {direction!r}")
        append_jsonl(
            self.path,
            {
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "direction": direction,
                "peer": peer,
                "text": text,
            },
        )

    def entries(self) -> list[dict]:
        return list(iter_jsonl(self.path))

    def recent(self, limit: int) -> list[dict]:
        return read_jsonl_tail(self.path, limit)
