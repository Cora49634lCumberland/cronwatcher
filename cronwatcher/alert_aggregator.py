"""Aggregates multiple alerts into a single batched summary for delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cronwatcher.alerting import Alert


@dataclass
class AlertBatch:
    """A collection of alerts grouped for delivery."""

    created_at: datetime = field(default_factory=datetime.utcnow)
    alerts: List[Alert] = field(default_factory=list)

    def add(self, alert: Alert) -> None:
        """Append an alert to this batch."""
        self.alerts.append(alert)

    @property
    def size(self) -> int:
        return len(self.alerts)

    @property
    def job_names(self) -> List[str]:
        return [a.job_name for a in self.alerts]

    def summary(self) -> str:
        if not self.alerts:
            return "No alerts in batch."
        lines = [f"Alert batch ({self.size} alerts) created at {self.created_at.isoformat()}:"]
        for alert in self.alerts:
            lines.append(f"  - {alert}")
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AlertBatch(size={self.size}, created_at={self.created_at!r})"


class AlertAggregator:
    """Buffers incoming alerts and flushes them as a batch.

    Useful when many jobs may drift simultaneously and you want to
    deliver a single consolidated notification rather than one per job.
    """

    def __init__(self, max_size: int = 50) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self._max_size = max_size
        self._pending: List[Alert] = []

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def collect(self, alert: Alert) -> Optional[AlertBatch]:
        """Add an alert to the buffer.

        Returns a flushed AlertBatch if max_size is reached, otherwise None.
        """
        self._pending.append(alert)
        if len(self._pending) >= self._max_size:
            return self.flush()
        return None

    def flush(self) -> AlertBatch:
        """Return all buffered alerts as a batch and clear the buffer."""
        batch = AlertBatch(alerts=list(self._pending))
        self._pending.clear()
        return batch

    def has_pending(self) -> bool:
        return bool(self._pending)
