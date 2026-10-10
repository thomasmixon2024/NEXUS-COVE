from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentStatus(StrEnum):
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class Task:
    prompt: str
    task_type: str = "general"
    required_capabilities: frozenset[str] = frozenset()
    priority: int = 0
    task_id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, frozen=True)
class TaskResult:
    task_id: str
    agent_id: str
    status: TaskStatus
    started_at: datetime
    finished_at: datetime
    output: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    measured_duration_seconds: float | None = None

    @property
    def duration_seconds(self) -> float:
        if self.measured_duration_seconds is not None:
            return max(0.0, self.measured_duration_seconds)
        return max(0.0, (self.finished_at - self.started_at).total_seconds())


@dataclass(slots=True)
class Agent:
    agent_id: str
    capabilities: frozenset[str] = frozenset()
    status: AgentStatus = AgentStatus.OFFLINE
    current_load: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
