"""Summarizes job execution history for reporting and diagnostics."""

from dataclasses import dataclass
from typing import List, Optional
from cronwatcher.history import JobHistory, ExecutionEvent


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration_seconds: Optional[float]
    last_run_timestamp: Optional[str]
    last_status: Optional[str]

    def __str__(self) -> str:
        last = self.last_run_timestamp or "never"
        avg = (
            f"{self.avg_duration_seconds:.2f}s"
            if self.avg_duration_seconds is not None
            else "n/a"
        )
        return (
            f"[{self.job_name}] runs={self.total_runs} "
            f"ok={self.successful_runs} fail={self.failed_runs} "
            f"avg_duration={avg} last_run={last} last_status={self.last_status or 'n/a'}"
        )


class HistoryReporter:
    def __init__(self, history: JobHistory) -> None:
        self._history = history

    def summarize_job(self, job_name: str) -> JobSummary:
        events: List[ExecutionEvent] = self._history.get_events(job_name)

        total = len(events)
        successful = sum(1 for e in events if e.status == "success")
        failed = sum(1 for e in events if e.status == "failure")

        durations = [
            e.duration_seconds
            for e in events
            if e.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else None

        last_event: Optional[ExecutionEvent] = events[-1] if events else None
        last_ts = last_event.executed_at if last_event else None
        last_status = last_event.status if last_event else None

        return JobSummary(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration_seconds=avg_duration,
            last_run_timestamp=last_ts,
            last_status=last_status,
        )

    def summarize_all(self) -> List[JobSummary]:
        return [
            self.summarize_job(name)
            for name in self._history.known_jobs()
        ]
