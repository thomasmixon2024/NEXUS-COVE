from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeMetrics:
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_in_flight: int = 0
    total_duration_seconds: float = 0.0

    def record_submission(self) -> None:
        self.tasks_submitted += 1
        self.tasks_in_flight += 1

    def record_result(self, duration_seconds: float, success: bool) -> None:
        self.tasks_in_flight = max(0, self.tasks_in_flight - 1)
        self.total_duration_seconds += duration_seconds
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1

    def snapshot(self) -> dict[str, float | int]:
        completed = self.tasks_completed + self.tasks_failed
        return {
            "tasks_submitted": self.tasks_submitted,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_in_flight": self.tasks_in_flight,
            "average_duration_seconds": self.total_duration_seconds / completed
            if completed
            else 0.0,
        }
