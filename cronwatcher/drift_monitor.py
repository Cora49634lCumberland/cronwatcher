"""DriftMonitor integrates DriftAnalyzer with HeartbeatTracker and AlertManager."""

from datetime import datetime, timezone
from typing import Optional

from cronwatcher.drift import DriftAnalyzer, DriftRecord
from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.alerting import Alert, AlertManager
from cronwatcher.scheduler import CronSchedule


class DriftMonitor:
    def __init__(
        self,
        heartbeat: HeartbeatTracker,
        alert_manager: AlertManager,
        threshold_seconds: float = 60.0,
    ) -> None:
        self.heartbeat = heartbeat
        self.alert_manager = alert_manager
        self.analyzer = DriftAnalyzer(threshold_seconds=threshold_seconds)

    def check_job(
        self,
        job_name: str,
        schedule: CronSchedule,
        now: Optional[datetime] = None,
    ) -> Optional[DriftRecord]:
        """Check a job for drift and emit an alert if threshold exceeded."""
        if now is None:
            now = datetime.now(tz=timezone.utc)

        record = self.heartbeat.get(job_name)
        if record is None or record.last_seen is None:
            return None

        expected = schedule.previous_run(now)
        if expected is None:
            return None

        drift_record = self.analyzer.record(
            job_name=job_name,
            expected_at=expected,
            actual_at=record.last_seen,
        )

        if self.analyzer.is_drifting(job_name):
            alert = Alert(
                job_name=job_name,
                reason=(
                    f"drift of {drift_record.drift_seconds:+.1f}s "
                    f"exceeds threshold {self.analyzer.threshold_seconds}s"
                ),
                last_seen=record.last_seen,
            )
            self.alert_manager.emit(alert)

        return drift_record
