#!/usr/bin/env python3
"""check_roundtrip.py - submit one task through the real server and workers.

Run this instead of the standalone manager. It connects as Nexus-Manager,
submits a task, waits for a worker to finish it, and reports the result.

Start first (separate windows):
    cove-server --host 127.0.0.1 --port 8765
    python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend
    python -m nexus_cove.agents.worker --name Vigil-Worker --capability analysis --test-backend
Then run:
    python scripts\\diagnostics\\check_roundtrip.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

URI = "ws://127.0.0.1:8765"
WAIT_SECONDS = 10.0
GREEN, RED, PURPLE, BRIGHT = "\033[32m", "\033[31m", "\033[35m", "\033[95m"
RESET = "\033[0m"


async def run_check() -> int:
    from nexus_cove.core.models import Task
    from nexus_cove.orchestration.manager import Manager
    from nexus_cove.storage.sqlite import SQLiteStorage

    db_path = Path(tempfile.gettempdir()) / "nexus_roundtrip.db"
    if db_path.exists():
        db_path.unlink()
    manager = Manager(URI, SQLiteStorage(str(db_path)))
    listener = None
    try:
        await manager.connect()
        listener = asyncio.create_task(manager.listen())
        await asyncio.wait_for(manager._ready.wait(), timeout=5)
        print(f"Workers registered: {len(manager.registry._agents)}")

        task_id = await manager.submit(Task(prompt="round-trip check", task_type="general"))
        print(f"Submitted task {task_id}")

        for _ in range(int(WAIT_SECONDS / 0.1)):
            if manager.metrics.tasks_completed or manager.metrics.tasks_failed:
                break
            await asyncio.sleep(0.1)

        completed = manager.metrics.tasks_completed
        failed = manager.metrics.tasks_failed
        assignee = manager.tasks.assignment(task_id)
        print(f"Assigned to : {assignee}")
        print(f"Completed   : {completed}   Failed: {failed}")
        return 0 if completed == 1 and failed == 0 else 1
    except TimeoutError:
        print(f"{RED}No worker registered within 5 seconds.{RESET}")
        return 1
    finally:
        if listener:
            listener.cancel()
        await manager.close()


def main() -> int:
    if os.name == "nt":
        os.system("")
    try:
        code = asyncio.run(run_check())
    except OSError as exc:
        print(f"{RED}[FAILURE] Cannot reach {URI}: {exc}{RESET}")
        print(f"{PURPLE}Suggested next actions:{RESET}")
        print(f"{PURPLE}  1. Start cove-server in its own window first.{RESET}")
        print(f"{BRIGHT}cove-server --host 127.0.0.1 --port 8765{RESET}")
        return 1
    if code == 0:
        print(
            f"{GREEN}[SUCCESS] Round trip completed: task assigned, executed, and recorded.{RESET}"
        )
        print(f"{PURPLE}Suggested next actions:{RESET}")
        print(f"{PURPLE}  1. Repeat the check with several tasks for a stability run.{RESET}")
    else:
        print(f"{RED}[FAILURE] Round trip did not complete.{RESET}")
        print(f"{PURPLE}Suggested next actions:{RESET}")
        print(f"{PURPLE}  1. Confirm both workers are running and registered.{RESET}")
    return code


if __name__ == "__main__":
    sys.exit(main())
