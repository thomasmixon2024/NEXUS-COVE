from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from nexus_cove.core.models import Task, TaskResult, TaskStatus


class DeterministicTestBackend:
    """Test-only backend. It creates no telemetry claims about model usage."""

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds

    async def execute(self, task: Task, agent_id: str) -> TaskResult:
        started = datetime.now(UTC)
        monotonic_start = time.monotonic()
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        finished = datetime.now(UTC)
        duration = time.monotonic() - monotonic_start
        return TaskResult(
            task_id=task.task_id,
            agent_id=agent_id,
            status=TaskStatus.COMPLETED,
            started_at=started,
            finished_at=finished,
            output=f"Test backend accepted task {task.task_id}",
            measured_duration_seconds=duration,
        )
