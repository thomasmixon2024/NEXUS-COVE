"""Per-agent knowledge: documents held by one agent and no other.

Each agent reads only its own folder, ``<data>/knowledge/<agent>/``. Thomas
fills it with the grant script. An agent may share an item with the agent
it is talking to by writing a line ``SHARE: <title>`` in a reply. Nothing is
shared unless the agent writes that line, and the worker strips the line
from the visible reply.
"""

from __future__ import annotations

import re
from pathlib import Path

from nexus_cove.agents.pause import data_dir

SHARE_PREFIX = "SHARE:"
MAX_ITEM_CHARS = 1500
MAX_ITEMS_IN_PROMPT = 4
EXTENSIONS = (".md", ".txt")
_VALID_AGENT = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def knowledge_folder(agent_id: str) -> Path:
    if not _VALID_AGENT.fullmatch(agent_id):
        raise ValueError(f"invalid agent name: {agent_id!r}")
    return data_dir() / "knowledge" / agent_id


class KnowledgeStore:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def items(self) -> dict[str, str]:
        """Map each item's title (file name without extension) to its text."""
        if not self.folder.is_dir():
            return {}
        found: dict[str, str] = {}
        for path in sorted(self.folder.iterdir()):
            if path.suffix.lower() in EXTENSIONS and path.is_file():
                found[path.stem] = path.read_text(encoding="utf-8", errors="replace")
        return found

    def find(self, title: str) -> str | None:
        wanted = title.strip().lower()
        for name, text in self.items().items():
            if name.lower() == wanted:
                return text
        return None


def parse_shares(reply: str) -> tuple[str, list[str]]:
    """Split a reply into the visible text and the titles the agent chose to share."""
    kept: list[str] = []
    titles: list[str] = []
    for line in reply.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith(SHARE_PREFIX):
            title = stripped[len(SHARE_PREFIX) :].strip()
            if title:
                titles.append(title)
        else:
            kept.append(line)
    return "\n".join(kept).strip(), titles
