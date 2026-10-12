import pytest

from nexus_cove.core.exceptions import AgentUnavailable
from nexus_cove.core.models import Task, TaskStatus
from nexus_cove.orchestration.manager import Manager


class RecordingStorage:
    def __init__(self) -> None:
        self.statuses: list[str] = []

    def initialize(self) -> None:
        return None

    def record_task(self, task, status: str) -> None:
        self.statuses.append(status)

    def update_task_status(self, task_id: str, status: str) -> None:
        self.statuses.append(status)

    def record_result(self, result) -> None:
        return None

    def close(self) -> None:
        return None


class RecordingSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, body: str) -> None:
        self.sent.append(body)


async def test_rejected_task_is_failed_not_orphaned() -> None:
    storage = RecordingStorage()
    manager = Manager("ws://unused", storage)
    socket = RecordingSocket()
    manager.websocket = socket
    task = Task(prompt="needs gpu", required_capabilities=frozenset({"gpu"}))

    with pytest.raises(AgentUnavailable):
        await manager.submit(task)

    assert manager.tasks.get_optional(task.task_id) is not None
    assert storage.statuses == [TaskStatus.FAILED.value]
    assert TaskStatus.QUEUED.value not in storage.statuses
    assert socket.sent == []
    assert manager.metrics.tasks_failed == 1