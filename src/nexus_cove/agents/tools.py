"""The two tools the agents asked for. Each returns real data or nothing.

- GeologyAnalyzer (Aegis-Worker): reports only rows that exist in
  reference/geology.csv for materials named in the message.
- PatternFinder (Vigil-Worker): counts words and questions in messages this
  agent has actually heard, from its own memory log.

A tool returns None when it has nothing to add, so it never adds noise.
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter
from pathlib import Path

from nexus_cove.agents.memory import AgentMemory

REFERENCE_DIR_ENV = "NEXUS_COVE_REFERENCE_DIR"
GEOLOGY_COLUMNS = ("material", "property", "value", "unit", "source")
PATTERN_TRIGGERS = ("pattern", "repeat", "most common", "how often", "trend")
MIN_MESSAGES_FOR_PATTERNS = 5
STOPWORDS = frozenset(
    "the and that with this what have from about would could should there their they your "
    "them were will just like into when than then some more been very also over only does "
    "know think being which where while would".split()
)


def reference_dir() -> Path:
    return Path(os.environ.get(REFERENCE_DIR_ENV, "reference"))


class GeologyAnalyzer:
    name = "Geology Analyzer"

    def __init__(self, path: Path) -> None:
        self.path = path

    def _rows(self) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = set(GEOLOGY_COLUMNS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{self.path.name} is missing columns: {sorted(missing)}")
            return [row for row in reader if (row.get("material") or "").strip()]

    def run(self, text: str) -> str | None:
        lowered = text.lower()
        hits = [row for row in self._rows() if row["material"].strip().lower() in lowered]
        if not hits:
            return None
        lines = [
            f"- {row['material']}: {row['property']} = {row['value']} {row['unit']} "
            f"(source: {row['source']})"
            for row in hits
        ]
        return "Geology Analyzer (from the reference file):\n" + "\n".join(lines)


class PatternFinder:
    name = "Pattern Finder"

    def __init__(self, memory: AgentMemory) -> None:
        self._memory = memory

    def run(self, text: str) -> str | None:
        if not any(trigger in text.lower() for trigger in PATTERN_TRIGGERS):
            return None
        heard = [
            entry["text"] for entry in self._memory.entries() if entry["direction"] == "received"
        ]
        if len(heard) < MIN_MESSAGES_FOR_PATTERNS:
            return (
                f"Pattern Finder: {len(heard)} message(s) heard so far; it needs "
                f"{MIN_MESSAGES_FOR_PATTERNS} before reporting patterns."
            )
        words = Counter(
            word
            for message in heard
            for word in re.findall(r"[a-z']+", message.lower())
            if len(word) >= 4 and word not in STOPWORDS
        )
        questions = sum(message.count("?") for message in heard)
        top = ", ".join(f"{word} ({count})" for word, count in words.most_common(5)) or "none"
        return (
            f"Pattern Finder (from {len(heard)} messages heard): most repeated words: {top}. "
            f"Questions heard: {questions}."
        )


def toolkit_for(agent_id: str, memory: AgentMemory) -> tuple:
    """Each agent gets only the tool it asked for."""
    if agent_id == "Aegis-Worker":
        return (GeologyAnalyzer(reference_dir() / "geology.csv"),)
    if agent_id == "Vigil-Worker":
        return (PatternFinder(memory),)
    return ()
