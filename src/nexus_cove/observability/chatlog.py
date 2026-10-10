"""Full record of Nexus Chat: one JSON line per message, appended as it happens.

The file is ``$NEXUS_COVE_LOG_DIR/nexus_chat.jsonl`` (default: ``logs``
relative to the working directory). Each message is written once, when the
server delivers it. Agent-to-agent copies made for the browser feed are not
written again.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from nexus_cove.utils.jsonl import append_jsonl, read_jsonl_tail

LOG_DIR_ENV = "NEXUS_COVE_LOG_DIR"
CHAT_LOG_NAME = "nexus_chat.jsonl"
MAX_ENTRIES_RETURNED = 10000


def chat_log_path() -> Path:
    return Path(os.environ.get(LOG_DIR_ENV, "logs")) / CHAT_LOG_NAME


class ChatLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        kind: str,
        sender: str,
        sender_kind: str,
        recipient: str | None,
        message: str,
    ) -> None:
        append_jsonl(
            self.path,
            {
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                "kind": kind,
                "sender": sender,
                "sender_kind": sender_kind,
                "recipient": recipient,
                "message": message,
            },
        )

    def read(self, limit: int = MAX_ENTRIES_RETURNED) -> list[dict]:
        return read_jsonl_tail(self.path, limit)
