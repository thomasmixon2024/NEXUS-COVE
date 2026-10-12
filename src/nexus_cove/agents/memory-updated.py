"""Per-agent memory: a log of what an agent heard and what it said.

Supports automated compaction, echo-stripping, and cache clearing to maintain
high-signal long-term memory for LLM workers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from nexus_cove.utils.jsonl import append_jsonl, iter_jsonl, read_jsonl_tail

DIRECTIONS = frozenset({"sent", "received", "summary"})

# Phrases commonly generated during model memory loops
ECHO_PHRASES = (
    "in the recent memory",
    "you heard that the conversation was about",
    "i'll provide more context about",
)


class AgentMemory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, direction: str, peer: str, text: str) -> None:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS!r}, got {direction!r}")
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
        raw_recent = read_jsonl_tail(self.path, limit * 2)
        filtered = []
        for entry in raw_recent:
            text_lower = entry.get("text", "").lower()
            if any(phrase in text_lower for phrase in ECHO_PHRASES):
                continue
            filtered.append(entry)
        return filtered[-limit:]

    def compress(self, max_entries: int = 15) -> None:
        """Prune verbatim echo phrases, deduplicate entries, and condense old history."""
        all_entries = self.entries()
        if len(all_entries) <= max_entries:
            return

        clean_entries = []
        seen_texts = set()

        for entry in all_entries:
            text = entry.get("text", "").strip()
            text_lower = text.lower()

            # Skip echo loops
            if any(phrase in text_lower for phrase in ECHO_PHRASES):
                continue

            # Deduplicate exact repeating phrases
            if text_lower in seen_texts:
                continue

            seen_texts.add(text_lower)
            clean_entries.append(entry)

        # Retain the most recent entries
        retained = clean_entries[-max_entries:]

        # Atomic rewrite of the memory log
        temp_path = self.path.with_suffix(".tmp")
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        with temp_path.open("w", encoding="utf-8") as f:
            for entry in retained:
                import json
                f.write(json.dumps(entry) + "\n")

        temp_path.replace(self.path)

    def clear_cache(self) -> None:
        """Clear all stored chat entries and reset the agent's memory file."""
        if self.path.exists():
            self.path.unlink()
