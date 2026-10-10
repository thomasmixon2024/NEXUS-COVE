from __future__ import annotations

from nexus_cove.core.models import Task, TaskStatus


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._statuses: dict[str, TaskStatus] = {}
        self._assignments: dict[str, str] = {}

    def add(self, task: Task) -> None:
        self._tasks[task.task_id] = task
        self._statuses[task.task_id] = TaskStatus.CREATED

    def status(self, task_id: str) -> TaskStatus:
        return self._statuses[task_id]

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        self._statuses[task_id] = status

    def assign(self, task_id: str, agent_id: str) -> None:
        self._assignments[task_id] = agent_id
        self.set_status(task_id, TaskStatus.ASSIGNED)

    def assignment(self, task_id: str) -> str | None:
        return self._assignments.get(task_id)

    def get(self, task_id: str) -> Task:
        return self._tasks[task_id]

    def get_optional(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)
