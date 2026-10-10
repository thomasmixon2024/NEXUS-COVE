from nexus_cove.core.models import Task, TaskStatus
from nexus_cove.orchestration.task_registry import TaskRegistry


def test_task_registry_tracks_assignment_and_status() -> None:
    registry = TaskRegistry()
    task = Task(prompt="x")
    registry.add(task)
    registry.set_status(task.task_id, TaskStatus.QUEUED)
    registry.assign(task.task_id, "agent-a")
    assert registry.status(task.task_id) == TaskStatus.ASSIGNED
    assert registry.assignment(task.task_id) == "agent-a"
