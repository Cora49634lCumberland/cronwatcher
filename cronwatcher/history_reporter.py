"""Generates human-readable summaries of job execution history."""

from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.history import JobHistory, ExecutionEvent


@dataclass
class JobSummary:
    """Aggregated statistics for a single job's execution history."""
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration_seconds: Optional[float]
    last_run_at: Optional[str]

    def __str__(self) -> str:
        success_rate = (
            f"{100 * self.successful_runs / self.total_runs:.1f}%"
            if self.total_runs > 0
            else "N/A"
        )
        avg = (
            f"{self.avg_duration_seconds:.2f}s"
            if self.avg_duration_seconds is not None
            else "N/A"
        )
        return (
            f"[{self.job_name}] runs={self.total_runs}, "
            f"success_rate={success_rate}, avg_duration={avg}, "
            f"last_run={self.last_run_at or 'never'}"
        )


class HistoryReporter:
    """Produces summaries from a JobHistory store."""

    def __init__(self, history: JobHistory) -> None:
        self._history = history

    def summarize_job(self, job_name: str) -> JobSummary:
        """Return a JobSummary for the given job name."""
        events: List[ExecutionEvent] = self._history.get_events(job_name)

        total = len(events)
        successful = sum(1 for e in events if e.success)
        failed = total - successful

        durations = [
            e.duration_seconds
            for e in events
            if e.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else None

        last_event = max(events, key=lambda e: e.executed_at, default=None)
        last_run_at = last_event.executed_at if last_event else None

        return JobSummary(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration_seconds=avg_duration,
            last_run_at=last_run_at,
        )

    def summarize_all(self) -> List[JobSummary]:
        """Return summaries for every job that has recorded history."""
        return [self.summarize_job(name) for name in self._history.job_names()]

    def report(self) -> str:
        """Render a full text report for all jobs."""
        summaries = self.summarize_all()
        if not summaries:
            return "No job history available."
        return "\n".join(str(s) for s in summaries)
