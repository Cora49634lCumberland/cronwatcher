"""Persistent execution history for cron jobs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class ExecutionEvent:
    job_name: str
    executed_at: float  # Unix timestamp
    expected_at: Optional[float] = None  # Unix timestamp
    drift_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionEvent":
        return cls(**data)

    @property
    def executed_dt(self) -> datetime:
        return datetime.fromtimestamp(self.executed_at)


@dataclass
class JobHistory:
    job_name: str
    events: List[ExecutionEvent] = field(default_factory=list)
    max_events: int = 100

    def record(self, event: ExecutionEvent) -> None:
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

    def last_n(self, n: int) -> List[ExecutionEvent]:
        return self.events[-n:]

    def average_drift(self) -> Optional[float]:
        drifts = [e.drift_seconds for e in self.events if e.drift_seconds is not None]
        if not drifts:
            return None
        return sum(drifts) / len(drifts)


class HistoryStore:
    """Loads and persists job execution history to a JSON file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._data: dict[str, JobHistory] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, "r") as f:
            raw = json.load(f)
        for job_name, job_data in raw.items():
            events = [ExecutionEvent.from_dict(e) for e in job_data.get("events", [])]
            self._data[job_name] = JobHistory(
                job_name=job_name,
                events=events,
                max_events=job_data.get("max_events", 100),
            )

    def save(self) -> None:
        raw = {
            name: {"events": [e.to_dict() for e in jh.events], "max_events": jh.max_events}
            for name, jh in self._data.items()
        }
        with open(self.path, "w") as f:
            json.dump(raw, f, indent=2)

    def get(self, job_name: str) -> JobHistory:
        if job_name not in self._data:
            self._data[job_name] = JobHistory(job_name=job_name)
        return self._data[job_name]

    def record_event(self, event: ExecutionEvent) -> None:
        self.get(event.job_name).record(event)
        self.save()

    def all_jobs(self) -> List[str]:
        return list(self._data.keys())
