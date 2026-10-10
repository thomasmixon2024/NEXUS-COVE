"""Full record of Nexus Chat: one JSON line per message, appended as it happens.

The file is ``$NEXUS_COVE_LOG_DIR/nexus_chat.jsonl`` (default: ``logs``
relative to the working directory). Each message is written once, when the
server delivers it. Agent-to-agent copies made for the browser feed are not
written again.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

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
        record = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "kind": kind,
            "sender": sender,
            "sender_kind": sender_kind,
            "recipient": recipient,
            "message": message,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read(self, limit: int = MAX_ENTRIES_RETURNED) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as handle:
            tail = deque((line for line in handle if line.strip()), maxlen=limit)
        return [json.loads(line) for line in tail]
