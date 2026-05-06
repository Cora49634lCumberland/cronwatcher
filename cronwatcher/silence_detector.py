"""Detects jobs that have gone silent (stopped reporting entirely)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.alerting import Alert, AlertManager


@dataclass
class SilenceReport:
    """Represents a detected silence event for a job."""
    job_name: str
    last_seen: Optional[datetime]
    silence_threshold_seconds: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def silence_duration_seconds(self) -> Optional[float]:
        """Seconds since the job was last seen, or None if never seen."""
        if self.last_seen is None:
            return None
        return (self.detected_at - self.last_seen).total_seconds()

    def __repr__(self) -> str:
        duration = (
            f"{self.silence_duration_seconds:.1f}s"
            if self.silence_duration_seconds is not None
            else "never seen"
        )
        return (
            f"SilenceReport(job={self.job_name!r}, "
            f"silent_for={duration}, "
            f"threshold={self.silence_threshold_seconds}s)"
        )


class SilenceDetector:
    """Checks tracked jobs for silence beyond their expected interval."""

    def __init__(
        self,
        tracker: HeartbeatTracker,
        alert_manager: AlertManager,
        multiplier: float = 2.0,
    ) -> None:
        self._tracker = tracker
        self._alert_manager = alert_manager
        self._multiplier = multiplier
        self._alerted: Dict[str, datetime] = {}

    def check_all(self) -> List[SilenceReport]:
        """Check every registered job and return silence reports for overdue ones."""
        reports: List[SilenceReport] = []
        for job_name, record in self._tracker.jobs.items():
            threshold = record.expected_interval_seconds * self._multiplier
            now = datetime.now(timezone.utc)
            last_seen = record.last_seen

            if last_seen is None:
                silent = True
            else:
                elapsed = (now - last_seen).total_seconds()
                silent = elapsed > threshold

            if silent:
                report = SilenceReport(
                    job_name=job_name,
                    last_seen=last_seen,
                    silence_threshold_seconds=threshold,
                    detected_at=now,
                )
                reports.append(report)
                self._maybe_alert(report)

        return reports

    def _maybe_alert(self, report: SilenceReport) -> None:
        """Fire an alert only if we haven't already alerted for this silence window."""
        last_alert = self._alerted.get(report.job_name)
        if last_alert is None or (
            report.detected_at - last_alert
        ).total_seconds() > report.silence_threshold_seconds:
            alert = Alert(
                job_name=report.job_name,
                message=repr(report),
                last_seen=report.last_seen,
            )
            self._alert_manager.trigger(alert)
            self._alerted[report.job_name] = report.detected_at
