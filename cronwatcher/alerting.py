"""Alerting module for cronwatcher.

Handles alert generation and dispatch when cron jobs are detected
as overdue or exhibiting execution drift.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from cronwatcher.heartbeat import HeartbeatTracker, JobRecord

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents a single alert event for a monitored job."""

    job_name: str
    message: str
    severity: str  # "warning" | "critical"
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None

    def __str__(self) -> str:
        last = self.last_seen.isoformat() if self.last_seen else "never"
        return (
            f"[{self.severity.upper()}] {self.triggered_at.isoformat()} "
            f"job={self.job_name!r} last_seen={last} — {self.message}"
        )


# A handler is any callable that accepts an Alert.
AlertHandler = Callable[[Alert], None]


def log_handler(alert: Alert) -> None:
    """Default handler: writes the alert to the Python logger."""
    if alert.severity == "critical":
        logger.critical(str(alert))
    else:
        logger.warning(str(alert))


class AlertManager:
    """Checks a HeartbeatTracker for overdue jobs and dispatches alerts."""

    def __init__(
        self,
        tracker: HeartbeatTracker,
        handlers: Optional[List[AlertHandler]] = None,
    ) -> None:
        self.tracker = tracker
        self.handlers: List[AlertHandler] = handlers if handlers is not None else [log_handler]
        self._fired: dict[str, datetime] = {}

    def add_handler(self, handler: AlertHandler) -> None:
        """Register an additional alert handler."""
        self.handlers.append(handler)

    def check_all(self) -> List[Alert]:
        """Inspect every tracked job and fire alerts for overdue ones.

        Returns the list of alerts that were dispatched in this call.
        """
        alerts: List[Alert] = []
        for job_name, record in self.tracker.jobs.items():
            if self.tracker.is_overdue(job_name):
                alert = self._build_alert(job_name, record)
                self._dispatch(alert)
                alerts.append(alert)
            else:
                # Clear previous fired state once the job is healthy again.
                self._fired.pop(job_name, None)
        return alerts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_alert(self, job_name: str, record: JobRecord) -> Alert:
        if record.last_seen is None:
            message = "Job has never been seen; expected interval exceeded."
            severity = "warning"
        else:
            overdue_by = datetime.utcnow() - record.last_seen
            message = f"Job overdue by {overdue_by}."
            severity = "critical" if overdue_by.total_seconds() > record.interval_seconds * 2 else "warning"
        return Alert(
            job_name=job_name,
            message=message,
            severity=severity,
            last_seen=record.last_seen,
        )

    def _dispatch(self, alert: Alert) -> None:
        self._fired[alert.job_name] = alert.triggered_at
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception:  # noqa: BLE001
                logger.exception("Alert handler %r raised an exception", handler)
