"""Cron schedule parsing and timing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from croniter import croniter


@dataclass
class CronSchedule:
    expression: str
    job_name: str
    grace_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not croniter.is_valid(self.expression):
            raise ValueError(f"Invalid cron expression: {self.expression!r}")

    @property
    def expected_interval_seconds(self) -> float:
        now = datetime.now(tz=timezone.utc)
        it = croniter(self.expression, now)
        t1 = it.get_next(datetime)
        t2 = it.get_next(datetime)
        return (t2 - t1).total_seconds()

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        base = after or datetime.now(tz=timezone.utc)
        it = croniter(self.expression, base)
        return it.get_next(datetime)

    def previous_run(self, before: Optional[datetime] = None) -> datetime:
        base = before or datetime.now(tz=timezone.utc)
        it = croniter(self.expression, base)
        return it.get_prev(datetime)

    def deadline_seconds(self) -> float:
        return self.expected_interval_seconds + self.grace_seconds


@dataclass
class ScheduleRegistry:
    _schedules: Dict[str, CronSchedule] = field(default_factory=dict)

    def register(self, schedule: CronSchedule) -> None:
        self._schedules[schedule.job_name] = schedule

    def get(self, job_name: str) -> Optional[CronSchedule]:
        return self._schedules.get(job_name)

    def all(self) -> List[CronSchedule]:
        return list(self._schedules.values())

    def remove(self, job_name: str) -> None:
        self._schedules.pop(job_name, None)

    def __len__(self) -> int:
        return len(self._schedules)
