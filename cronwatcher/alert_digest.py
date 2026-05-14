"""Periodic digest of accumulated alerts, grouped by job and kind."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.alert_aggregator import AlertBatch
from cronwatcher.alerting import Alert
from cronwatcher.notifier import NotifierBase

logger = logging.getLogger(__name__)


@dataclass
class DigestReport:
    """Immutable snapshot of a flushed digest."""

    generated_at: datetime
    batches: List[AlertBatch] = field(default_factory=list)

    @property
    def total_alerts(self) -> int:
        return sum(b.size for b in self.batches)

    def __str__(self) -> str:
        lines = [f"Digest @ {self.generated_at.isoformat()} — {self.total_alerts} alert(s)"]
        for batch in self.batches:
            lines.append(f"  [{batch.kind}] {batch.size} alert(s): {', '.join(sorted(batch.job_names))}")
        return "\n".join(lines)


class AlertDigest:
    """Accumulates alerts and flushes a DigestReport to notifiers on demand."""

    def __init__(self, notifiers: Optional[List[NotifierBase]] = None) -> None:
        self._notifiers: List[NotifierBase] = notifiers or []
        self._batches: dict[str, AlertBatch] = {}

    def add(self, alert: Alert) -> None:
        """Stage an alert into the appropriate batch (keyed by kind)."""
        if alert.kind not in self._batches:
            self._batches[alert.kind] = AlertBatch(kind=alert.kind)
        self._batches[alert.kind].add(alert)

    def pending_count(self) -> int:
        return sum(b.size for b in self._batches.values())

    def flush(self) -> DigestReport:
        """Build a DigestReport, dispatch it to all notifiers, then reset state."""
        report = DigestReport(
            generated_at=datetime.now(timezone.utc),
            batches=list(self._batches.values()),
        )
        if report.total_alerts == 0:
            logger.debug("AlertDigest.flush called with no pending alerts")
            self._batches.clear()
            return report

        digest_alert = Alert(
            job_name="__digest__",
            kind="digest",
            message=str(report),
        )
        for notifier in self._notifiers:
            try:
                notifier.send(digest_alert)
            except Exception:
                logger.exception("Notifier %s failed during digest flush", notifier)

        self._batches.clear()
        return report
