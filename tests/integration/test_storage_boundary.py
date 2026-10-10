from nexus_cove.core.models import Task, TaskStatus
from nexus_cove.storage.sqlite import SQLiteStorage


def test_storage_boundary_does_not_require_or_import_transport(tmp_path) -> None:
    storage = SQLiteStorage(tmp_path / "integration.db")
    storage.initialize()
    task = Task(prompt="boundary")
    storage.record_task(task, TaskStatus.QUEUED.value)
    assert storage.recent_results() == []
    storage.close()
