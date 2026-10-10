from __future__ import annotations

import sqlite3
from pathlib import Path

from nexus_cove.core.models import Task, TaskResult


class SQLiteStorage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys = ON")

        # Create schema version table if it doesn't exist
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )"""
        )

        # Get current schema version
        cursor = self.connection.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row else None

        # If no version exists, this is a fresh install - set to version 1
        if current_version is None:
            current_version = 1
            self.connection.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (current_version,)
            )
            self.connection.commit()

        # Apply migrations if needed
        self._migrate_to_current(current_version)

        # Create core tables (using IF NOT EXISTS to be safe)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                output TEXT,
                error TEXT,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_task ON task_results(task_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_agent ON task_results(agent_id)"
        )
        self.connection.commit()

    def _require_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("Storage is not initialized")
        return self.connection

    def _migrate_to_current(self, current_version: int) -> None:
        """Migrate the database schema to the current version.

        This method applies any necessary schema updates to bring the database
        from its current version to the latest schema version defined in this code.
        All migrations must be backward compatible and preserve existing data.
        """
        # Currently, the latest schema version is 1 (the initial schema)
        # Future versions would be handled here
        LATEST_SCHEMA_VERSION = 1

        if current_version > LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than "
                f"expected version {LATEST_SCHEMA_VERSION}. "
                "Please update the application to a compatible version."
            )

        # Apply migrations from current_version to LATEST_SCHEMA_VERSION
        # Each version transition should have its own migration logic
        while current_version < LATEST_SCHEMA_VERSION:
            next_version = current_version + 1
            try:
                self._migrate_to_version(next_version)
                current_version = next_version

                # Update the stored version
                self.connection.execute("UPDATE schema_version SET version = ?", (current_version,))
                self.connection.commit()

            except Exception as e:
                self.connection.rollback()
                raise RuntimeError(
                    f"Failed to migrate from version {current_version} to {next_version}: {e}"
                ) from e

    def _migrate_to_version(self, target_version: int) -> None:
        """Apply migration to reach the target version.

        This method should contain the specific logic for migrating from
        version (target_version - 1) to target_version.
        """
        # For now, since we're starting at version 1 and LATEST_SCHEMA_VERSION is 1,
        # no migrations are needed. Future migrations would be added here.
        #
        # Example structure for future migrations:
        # if target_version == 2:
        #     self.connection.execute(
        #         "ALTER TABLE tasks ADD COLUMN new_column TEXT DEFAULT 'default_value'"
        #     )
        # elif target_version == 3:
        #     self.connection.execute(
        #         "CREATE INDEX IF NOT EXISTS idx_new ON task_results(new_column)"
        #     )
        pass

    def record_task(self, task: Task, status: str) -> None:
        conn = self._require_connection()
        conn.execute(
            "INSERT OR REPLACE INTO tasks("
            "task_id, task_type, prompt, priority, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                task.task_id,
                task.task_type,
                task.prompt,
                task.priority,
                status,
                task.created_at.isoformat(),
            ),
        )
        conn.commit()

    def update_task_status(self, task_id: str, status: str) -> None:
        conn = self._require_connection()
        conn.execute("UPDATE tasks SET status=? WHERE task_id=?", (status, task_id))
        conn.commit()

    def record_result(self, result: TaskResult) -> None:
        conn = self._require_connection()
        conn.execute(
            """INSERT INTO task_results
               (task_id, agent_id, status, started_at, finished_at, duration_seconds, output, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.task_id,
                result.agent_id,
                result.status.value,
                result.started_at.isoformat(),
                result.finished_at.isoformat(),
                result.duration_seconds,
                result.output,
                result.error,
            ),
        )
        self.update_task_status(result.task_id, result.status.value)
        conn.commit()

    def recent_results(self, limit: int = 100) -> list[dict[str, object]]:
        conn = self._require_connection()
        rows = conn.execute(
            """SELECT task_id, agent_id, status, started_at, finished_at,
                      duration_seconds, output, error
               FROM task_results ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "task_id": row[0],
                "agent_id": row[1],
                "status": row[2],
                "started_at": row[3],
                "finished_at": row[4],
                "duration_seconds": row[5],
                "output": row[6],
                "error": row[7],
            }
            for row in rows
        ]

    def summary(self) -> dict[str, float | int]:
        conn = self._require_connection()
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(AVG(duration_seconds), 0), "
            "COALESCE(SUM(status = 'completed'), 0) FROM task_results"
        ).fetchone()
        total = int(row[0])
        completed = int(row[2])
        return {
            "total_results": total,
            "average_duration_seconds": float(row[1]),
            "success_rate": (completed / total) if total else 0.0,
        }

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> SQLiteStorage:
        self.initialize()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
