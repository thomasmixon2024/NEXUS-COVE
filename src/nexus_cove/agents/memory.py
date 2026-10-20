"""Per-agent memory: a log of what an agent heard and what it said.

Each agent appends one JSON line per message to its own file. Entries are
never edited, rotated or removed. The worker puts the most recent entries
into each prompt, so an agent can refer back to earlier conversation.

Next to the message log the class keeps small sidecar files, all named after
the agent so agents sharing a directory never overwrite each other:

- ``<agent>.highlights.json``: the last MAX_HIGHLIGHTS lines that looked like
  bullet points, decisions, errors and similar.
- ``checkpoints/<agent>_checkpoint_<time>.json``: a snapshot written every
  ``checkpoint_every`` messages, or on request.
- ``session/<agent>.sessions.jsonl`` and ``session/<agent>.current.json``: a
  short journal of agent start-ups, capped at MAX_SESSION_CHECKPOINTS lines.

The message count is read from disk once per instance and then tracked in
memory, so ``append`` does constant work. Two instances appending to the same
file at the same time may report slightly stale counts; the log itself stays
correct.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nexus_cove.utils.jsonl import append_jsonl, iter_jsonl, read_jsonl_tail

logger = logging.getLogger(__name__)

DIRECTIONS = frozenset({"sent", "received"})
CHECKPOINT_EVERY = 100
MAX_HIGHLIGHTS = 50
MAX_SESSION_CHECKPOINTS = 50

# A line is a highlight if it is a bullet, numbered item or quote, or contains a
# keyword at the start of a word ("fixed" matches, "prefix" does not).
_HIGHLIGHT = re.compile(
    r"^\s*(?:[-*•]\s|\d+\.\s|>\s)"
    r"|\b(?:key\s+point|important|decision|error|success|todo|fix|critical)",
    re.IGNORECASE,
)
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _safe_name(name: str) -> str:
    """Make an agent name safe to use inside a file name."""
    return _UNSAFE_NAME_CHARS.sub("_", name)[:80] or "unknown"


def _write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON so a crash never leaves a half-written file behind."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_json(path: Path) -> Any | None:
    """Return parsed JSON, or None if the file is missing or unreadable (logged)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        logger.warning("ignoring unreadable memory file %s", path, exc_info=True)
        return None


def _read_jsonl_tolerant(path: Path) -> list[dict]:
    """Read a JSONL file, skipping (and logging) lines that are not valid JSON."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    items: list[dict] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except ValueError:
            logger.warning("skipping corrupt line %d in %s", number, path)
    return items


class AgentMemory:
    def __init__(self, path: Path, agent_name: str | None = None) -> None:
        self.path = path
        # Workers pass only the path, so default to the file name ("Aegis-Worker").
        self.agent_name = _safe_name(agent_name or path.stem)
        base = path.parent
        self._highlight_file = base / f"{self.agent_name}.highlights.json"
        self._checkpoint_dir = base / "checkpoints"
        self._session_dir = base / "session"
        self._session_journal = self._session_dir / f"{self.agent_name}.sessions.jsonl"
        self._current_session_file = self._session_dir / f"{self.agent_name}.current.json"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._session_dir.mkdir(parents=True, exist_ok=True)

        self.checkpoint_every = CHECKPOINT_EVERY
        self._message_count: int | None = None
        self._highlights = self._load_highlights()
        self._initialize_session_continuity()

    # --- message log -------------------------------------------------------

    def append(self, direction: str, peer: str, text: str) -> None:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be 'sent' or 'received', got {direction!r}")

        count = self._count()  # read before appending so the new line is not counted twice
        entry = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "direction": direction,
            "peer": peer,
            "text": text,
        }
        append_jsonl(self.path, entry)
        self._message_count = count + 1

        # The message is already stored; a failure in the extras must not lose it.
        try:
            self._extract_and_preserve_highlights(text)
            if self._message_count % self.checkpoint_every == 0:
                self.save_checkpoint(f"Automatic checkpoint at {self._message_count} messages")
        except OSError:
            logger.warning("memory housekeeping failed for %s", self.agent_name, exc_info=True)

    def entries(self) -> list[dict]:
        return list(iter_jsonl(self.path))

    def recent(self, limit: int) -> list[dict]:
        return read_jsonl_tail(self.path, limit)

    def _count(self) -> int:
        if self._message_count is None:
            self._message_count = sum(1 for _ in iter_jsonl(self.path))
        return self._message_count

    # --- highlights --------------------------------------------------------

    def get_highlights(self) -> list[str]:
        """Return the preserved highlight lines, oldest first."""
        return list(self._highlights)

    def _load_highlights(self) -> list[str]:
        data = _read_json(self._highlight_file)
        items = data.get("highlights") if isinstance(data, dict) else None
        return [h for h in items if isinstance(h, str)] if isinstance(items, list) else []

    def _extract_and_preserve_highlights(self, text: str) -> None:
        added = False
        for raw in text.splitlines():
            line = raw.strip()
            if line and _HIGHLIGHT.search(line) and line not in self._highlights:
                self._highlights.append(line)
                added = True
        if added:  # only touch the disk when something changed
            del self._highlights[:-MAX_HIGHLIGHTS]
            _write_json_atomic(
                self._highlight_file,
                {
                    "agent_name": self.agent_name,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "highlights": self._highlights,
                },
            )

    # --- snapshots ---------------------------------------------------------

    def save_checkpoint(self, description: str = "") -> str:
        """Write a snapshot (counts, highlights, last 10 entries); return its path."""
        now = datetime.now(UTC)
        name = f"{self.agent_name}_checkpoint_{now:%Y%m%d_%H%M%S_%f}.json"
        checkpoint_path = self._checkpoint_dir / name
        _write_json_atomic(
            checkpoint_path,
            {
                "timestamp": now.isoformat(),
                "agent_name": self.agent_name,
                "description": description,
                "message_count": self._count(),
                "highlights": self.get_highlights(),
                "recent_entries": self.recent(10),
            },
        )
        return str(checkpoint_path)

    def load_latest_checkpoint(self) -> dict | None:
        """Return the newest snapshot for this agent, or None."""
        candidates = list(self._checkpoint_dir.glob(f"{self.agent_name}_checkpoint_*.json"))
        if not candidates:
            return None
        latest = max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))
        data = _read_json(latest)
        return data if isinstance(data, dict) else None

    # --- session continuity ------------------------------------------------

    def _initialize_session_continuity(self) -> None:
        self.create_session_checkpoint(
            task_description="Agent session initialized",
            accomplishments=["Agent memory system started"],
            next_steps=["Ready to process messages"],
            metadata={"agent_name": self.agent_name, "startup": True},
        )

    def create_session_checkpoint(
        self,
        task_description: str,
        accomplishments: list[str],
        next_steps: list[str] | None = None,
        metadata: dict | None = None,
    ) -> str:
        now = datetime.now(UTC)
        checkpoint = {
            "timestamp": now.isoformat(),
            "session_id": f"{self.agent_name}_{int(now.timestamp())}",
            "agent_name": self.agent_name,
            "task_description": task_description,
            "accomplishments": accomplishments,
            "next_steps": next_steps or [],
            "metadata": metadata or {},
            "checkpoint_id": f"sc_{self.agent_name}_{now:%Y%m%d_%H%M%S_%f}",
            "message_count": self._count(),
            "highlight_count": len(self._highlights),
        }
        with open(self._session_journal, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(checkpoint) + "\n")
        _write_json_atomic(self._current_session_file, checkpoint)
        self._trim_session_journal()
        return checkpoint["checkpoint_id"]

    def _trim_session_journal(self) -> None:
        items = _read_jsonl_tolerant(self._session_journal)
        if len(items) <= MAX_SESSION_CHECKPOINTS:
            return
        keep = items[-MAX_SESSION_CHECKPOINTS:]
        fd, tmp = tempfile.mkstemp(dir=self._session_dir, prefix=".journal.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.writelines(json.dumps(item) + "\n" for item in keep)
            os.replace(tmp, self._session_journal)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def get_latest_session_checkpoint(self) -> dict | None:
        data = _read_json(self._current_session_file)
        return data if isinstance(data, dict) else None

    def get_session_checkpoint_history(self, limit: int = 10) -> list[dict]:
        """Return up to ``limit`` session checkpoints, newest first."""
        return list(reversed(_read_jsonl_tolerant(self._session_journal)))[:limit]

    def print_session_continuity_guide(self) -> None:
        latest = self.get_latest_session_checkpoint()
        if not latest:
            print(f"Agent {self.agent_name}: no previous session found - starting fresh")
            return
        print(f"AGENT SESSION CONTINUITY GUIDE - {self.agent_name}")
        print(f"Last session: {latest.get('timestamp', 'unknown')}")
        print(f"Task: {latest.get('task_description', 'not recorded')}")
        for title, key in (("Accomplishments", "accomplishments"), ("Next steps", "next_steps")):
            print(f"{title}:")
            for item in latest.get(key, []):
                print(f"  - {item}")
        print(
            f"Stats: {latest.get('message_count', '?')} messages, "
            f"{latest.get('highlight_count', '?')} highlights"
        )

    def startup_flush_with_highlight_retention(self) -> dict:
        """Report the retained highlights and record a start-up checkpoint.

        Nothing is deleted or rotated: the message log and highlights are left as is.
        """
        highlights = self.get_highlights()
        message_count = self._count()
        self.create_session_checkpoint(
            task_description="Startup flush performed",
            accomplishments=[
                f"Preserved {len(highlights)} highlights from {message_count} previous messages",
                "Session continuity maintained",
            ],
            next_steps=["Ready for fresh context with preserved insights"],
            metadata={"flush_performed": True, "highlight_count": len(highlights)},
        )
        return {
            "flush_performed": True,
            "highlights_preserved": highlights,
            "highlight_count": len(highlights),
            "message_count_before_flush": message_count,
            "status": "Ready for fresh context with preserved insights",
        }
