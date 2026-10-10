from datetime import UTC, datetime

from nexus_cove.core.models import Task, TaskResult, TaskStatus
from nexus_cove.storage.sqlite import SQLiteStorage


def test_sqlite_persists_real_result(tmp_path) -> None:
    db = SQLiteStorage(tmp_path / "cove.db")
    db.initialize()
    task = Task(prompt="persist me")
    db.record_task(task, TaskStatus.QUEUED.value)
    now = datetime.now(UTC)
    db.record_result(
        TaskResult(
            task_id=task.task_id,
            agent_id="Aegis",
            status=TaskStatus.COMPLETED,
            started_at=now,
            finished_at=now,
            output="actual result",
            measured_duration_seconds=0.125,
        )
    )
    assert db.recent_results(1)[0]["output"] == "actual result"
    assert db.summary()["success_rate"] == 1.0
    db.close()
