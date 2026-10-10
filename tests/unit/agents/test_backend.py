import asyncio

from nexus_cove.agents.backends.deterministic_backend import DeterministicTestBackend
from nexus_cove.core.models import Task, TaskStatus


def test_test_backend_reports_measured_runtime() -> None:
    result = asyncio.run(DeterministicTestBackend(0.001).execute(Task(prompt="x"), "agent"))
    assert result.status == TaskStatus.COMPLETED
    assert result.duration_seconds >= 0.0
    assert result.measured_duration_seconds is not None
