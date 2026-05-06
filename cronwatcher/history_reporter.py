"""Generates summary reports from job execution history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.history import HistoryStore, JobHistory


@dataclass
class JobSummary:
    job_name: str
    total_executions: int
    average_drift_seconds: Optional[float]
    max_drift_seconds: Optional[float]
    last_executed_at: Optional[float]

    def __str__(self) -> str:
        last = (
            f"{self.last_executed_at:.0f}"
            if self.last_executed_at is not None
            else "never"
        )
        avg = (
            f"{self.average_drift_seconds:.1f}s"
            if self.average_drift_seconds is not None
            else "n/a"
        )
        max_d = (
            f"{self.max_drift_seconds:.1f}s"
            if self.max_drift_seconds is not None
            else "n/a"
        )
        return (
            f"[{self.job_name}] executions={self.total_executions} "
            f"avg_drift={avg} max_drift={max_d} last_seen={last}"
        )


class HistoryReporter:
    """Produces human-readable and structured summaries from a HistoryStore."""

    def __init__(self, store: HistoryStore) -> None:
        self.store = store

    def summarize_job(self, job_name: str) -> JobSummary:
        jh: JobHistory = self.store.get(job_name)
        events = jh.events

        drifts = [e.drift_seconds for e in events if e.drift_seconds is not None]
        avg_drift = (sum(drifts) / len(drifts)) if drifts else None
        max_drift = max(drifts, default=None)
        last_exec = events[-1].executed_at if events else None

        return JobSummary(
            job_name=job_name,
            total_executions=len(events),
            average_drift_seconds=avg_drift,
            max_drift_seconds=max_drift,
            last_executed_at=last_exec,
        )

    def summarize_all(self) -> List[JobSummary]:
        return [self.summarize_job(name) for name in self.store.all_jobs()]

    def report_text(self) -> str:
        summaries = self.summarize_all()
        if not summaries:
            return "No job history available."
        return "\n".join(str(s) for s in summaries)
