"""Detects when a previously failing or silent job has recovered."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.alerting import Alert, AlertManager


@dataclass
class RecoveryEvent:
    job_name: str
    recovered_at: datetime
    silent_since: Optional[datetime] = None

    def __repr__(self) -> str:
        silent_info = (
            f", was silent since {self.silent_since.isoformat()}"
            if self.silent_since
            else ""
        )
        return (
            f"RecoveryEvent(job={self.job_name!r}, "
            f"recovered_at={self.recovered_at.isoformat()}{silent_info})"
        )


class RecoveryDetector:
    """Tracks jobs that were previously overdue and emits recovery alerts."""

    def __init__(
        self,
        tracker: HeartbeatTracker,
        alert_manager: AlertManager,
    ) -> None:
        self._tracker = tracker
        self._alert_manager = alert_manager
        # job_name -> datetime when we first noticed it was overdue
        self._overdue_since: dict[str, datetime] = {}

    def check_job(self, job_name: str, interval_seconds: float) -> Optional[RecoveryEvent]:
        """Check a job for recovery.  Returns a RecoveryEvent if it just recovered."""
        record = self._tracker.get(job_name)
        if record is None:
            return None

        currently_overdue = self._tracker.is_overdue(job_name, interval_seconds)

        if currently_overdue:
            # Record when we first noticed the outage
            if job_name not in self._overdue_since:
                self._overdue_since[job_name] = datetime.utcnow()
            return None

        if job_name in self._overdue_since:
            # Job was overdue but is healthy again
            silent_since = self._overdue_since.pop(job_name)
            event = RecoveryEvent(
                job_name=job_name,
                recovered_at=record.last_seen,  # type: ignore[arg-type]
                silent_since=silent_since,
            )
            alert = Alert(
                job_name=job_name,
                message=(
                    f"Job '{job_name}' has recovered. "
                    f"Last seen: {record.last_seen}. "
                    f"Was overdue since: {silent_since}."
                ),
                severity="info",
                last_seen=record.last_seen,
            )
            self._alert_manager.emit(alert)
            return event

        return None

    @property
    def overdue_jobs(self) -> list[str]:
        """Return names of jobs currently tracked as overdue."""
        return list(self._overdue_since.keys())
