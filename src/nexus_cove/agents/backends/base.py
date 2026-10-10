from __future__ import annotations

from typing import Protocol

from nexus_cove.core.models import Task, TaskResult


class AgentBackend(Protocol):
    async def execute(self, task: Task, agent_id: str) -> TaskResult: ...
