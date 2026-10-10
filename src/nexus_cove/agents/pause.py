"""Pause switches for agents.

Two levels:
- Global: while ``<data>/PAUSE`` exists, every agent and the manager stay silent.
- Per agent: while ``<data>/paused/<agent>.flag`` exists, that one agent stays
  silent. It ignores direct messages, group messages, and its conversation
  starter until resumed.

The data directory is ``$NEXUS_COVE_DATA_DIR`` if set, otherwise ``data``
relative to the current working directory. Agent names are restricted to
letters, digits, hyphens and underscores, so a name cannot escape that folder.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

DATA_DIR_ENV = "NEXUS_COVE_DATA_DIR"
PAUSE_FILE_NAME = "PAUSE"
PAUSED_DIR_NAME = "paused"
_VALID_AGENT = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def data_dir() -> Path:
    return Path(os.environ.get(DATA_DIR_ENV, "data"))


def pause_file() -> Path:
    return data_dir() / PAUSE_FILE_NAME


def is_paused() -> bool:
    return pause_file().exists()


def _agent_flag(agent_id: str) -> Path:
    if not _VALID_AGENT.fullmatch(agent_id):
        raise ValueError(f"invalid agent name for pause flag: {agent_id!r}")
    return data_dir() / PAUSED_DIR_NAME / f"{agent_id}.flag"


def is_agent_paused(agent_id: str) -> bool:
    """True if this agent is paused, either individually or by the global switch."""
    return is_paused() or _agent_flag(agent_id).exists()


def set_agent_paused(agent_id: str, paused: bool) -> None:
    flag = _agent_flag(agent_id)
    if paused:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()
    elif flag.exists():
        flag.unlink()
