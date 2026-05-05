"""Cron schedule parsing and next-run prediction for cronwatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

try:
    from croniter import croniter
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "croniter is required for schedule parsing: pip install croniter"
    ) from exc


@dataclass
class CronSchedule:
    """Wraps a cron expression and provides timing utilities."""

    job_name: str
    expression: str
    # Optional human-readable description
    description: str = ""
    # Tolerance window (seconds) added on top of the nominal interval
    tolerance_seconds: int = 60

    def __post_init__(self) -> None:
        if not croniter.is_valid(self.expression):
            raise ValueError(
                f"Invalid cron expression {self.expression!r} for job {self.job_name!r}"
            )

    def expected_interval_seconds(self) -> float:
        """Return the average interval between two consecutive runs (in seconds)."""
        now = datetime.now(tz=timezone.utc)
        it = croniter(self.expression, now)
        next1: datetime = it.get_next(datetime)
        next2: datetime = it.get_next(datetime)
        return (next2 - next1).total_seconds()

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Return the next scheduled run time after *after* (defaults to now)."""
        base = after or datetime.now(tz=timezone.utc)
        it = croniter(self.expression, base)
        return it.get_next(datetime)

    def deadline_seconds(self) -> float:
        """Interval + tolerance — used by HeartbeatTracker as the overdue window."""
        return self.expected_interval_seconds() + self.tolerance_seconds


class ScheduleRegistry:
    """Holds all registered CronSchedule objects, keyed by job name."""

    def __init__(self) -> None:
        self._schedules: dict[str, CronSchedule] = {}

    def register(self, schedule: CronSchedule) -> None:
        """Add or replace a schedule entry."""
        self._schedules[schedule.job_name] = schedule

    def get(self, job_name: str) -> Optional[CronSchedule]:
        return self._schedules.get(job_name)

    def all_schedules(self) -> list[CronSchedule]:
        return list(self._schedules.values())

    def deadline_for(self, job_name: str) -> Optional[float]:
        """Convenience: return deadline_seconds for a registered job or None."""
        schedule = self.get(job_name)
        return schedule.deadline_seconds() if schedule else None

    def __len__(self) -> int:
        return len(self._schedules)
