from datetime import UTC, datetime

from nexus_cove.core.models import Task, TaskResult, TaskStatus


def test_task_has_stable_identity_and_defaults() -> None:
    task = Task(prompt="inspect repository")
    assert task.task_id
    assert task.task_type == "general"
    assert task.required_capabilities == frozenset()


def test_result_uses_authoritative_measured_duration() -> None:
    now = datetime.now(UTC)
    result = TaskResult(
        task_id="t1",
        agent_id="a1",
        status=TaskStatus.COMPLETED,
        started_at=now,
        finished_at=now,
        measured_duration_seconds=0.42,
    )
    assert result.duration_seconds == 0.42
