#!/usr/bin/env python3
"""Checkpoint helper for Claude Code sessions (library and `status`/`history` CLI).

Writes the same files as save_checkpoint.py (the SessionEnd hook and the
manual `--file` path), so prefer that script for saving. This module remains
for code that imports SessionCheckpoint.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class SessionCheckpoint:
    def __init__(self, session_dir: Optional[Path] = None):
        if session_dir is None:
            # This file lives in .claude/memory, so never depend on the caller's cwd.
            session_dir = Path(__file__).resolve().parent

        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.session_dir / "session_checkpoints.jsonl"
        self.current_checkpoint = self.session_dir / "current_checkpoint.json"

    def create_checkpoint(self, task_description: str, accomplishments: List[str],
                          next_steps: Optional[List[str]] = None,
                          metadata: Optional[Dict] = None) -> str:
        """Create a new checkpoint entry and return its id."""
        now = datetime.now(timezone.utc)
        checkpoint = {
            "timestamp": now.isoformat(),
            "session_id": os.getenv("CLAUDE_SESSION_ID", "unknown"),
            "task_description": task_description,
            "accomplishments": accomplishments,
            "next_steps": next_steps or [],
            "metadata": metadata or {},
            "source": "manual",
            "checkpoint_id": f"cp_{now:%Y%m%d_%H%M%S}",
        }
        with open(self.checkpoint_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(checkpoint) + "\n")
        with open(self.current_checkpoint, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2)
        return checkpoint["checkpoint_id"]

    def get_latest_checkpoint(self) -> Optional[Dict]:
        try:
            return json.loads(self.current_checkpoint.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def get_checkpoint_history(self, limit: int = 10) -> List[Dict]:
        """Most recent first. Lines that are not valid JSON are skipped."""
        try:
            lines = self.checkpoint_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        checkpoints = []
        for line in lines:
            try:
                checkpoints.append(json.loads(line))
            except ValueError:
                continue
        return checkpoints[::-1][:limit]

    def print_session_continuity_guide(self) -> None:
        latest = self.get_latest_checkpoint()
        if not latest:
            print("No previous session found - starting fresh")
            return
        print("SESSION CONTINUITY GUIDE")
        print(f"Last session: {latest.get('timestamp', 'unknown')}")
        print(f"Task: {latest.get('task_description', 'not recorded')}")
        for title, key in (("Accomplishments", "accomplishments"), ("Next steps", "next_steps")):
            print(f"{title}:")
            for item in latest.get(key, []):
                print(f"   - {item}")


def main() -> None:
    checkpoint = SessionCheckpoint()
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "status":
        checkpoint.print_session_continuity_guide()
    elif command == "history":
        print("Recent checkpoint history:")
        for i, cp in enumerate(checkpoint.get_checkpoint_history(5), 1):
            print(f"{i}. [{cp.get('checkpoint_id')}] {cp.get('task_description')} ({cp.get('timestamp')})")
    else:
        print("Usage: checkpoint_system.py [status|history]")


if __name__ == "__main__":
    main()
