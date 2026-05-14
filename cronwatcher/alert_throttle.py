"""Alert throttling: suppress repeated alerts for the same job within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatcher.alerting import Alert


@dataclass
class ThrottleEntry:
    job_name: str
    alert_kind: str
    first_sent_at: float
    last_sent_at: float
    send_count: int = 1

    def seconds_since_last(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        return now - self.last_sent_at

    def __repr__(self) -> str:
        return (
            f"ThrottleEntry(job={self.job_name!r}, kind={self.alert_kind!r}, "
            f"count={self.send_count}, last_sent_at={self.last_sent_at:.1f})"
        )


class AlertThrottle:
    """Suppress duplicate alerts for the same (job, kind) pair within a cooldown period."""

    def __init__(self, cooldown_seconds: float = 300.0) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.cooldown_seconds = cooldown_seconds
        self._entries: Dict[tuple, ThrottleEntry] = {}

    def _key(self, alert: Alert) -> tuple:
        return (alert.job_name, alert.kind)

    def is_suppressed(self, alert: Alert, now: Optional[float] = None) -> bool:
        """Return True if the alert should be suppressed (sent too recently)."""
        now = now if now is not None else time.time()
        key = self._key(alert)
        entry = self._entries.get(key)
        if entry is None:
            return False
        return entry.seconds_since_last(now) < self.cooldown_seconds

    def record_sent(self, alert: Alert, now: Optional[float] = None) -> None:
        """Record that an alert was dispatched."""
        now = now if now is not None else time.time()
        key = self._key(alert)
        existing = self._entries.get(key)
        if existing is None:
            self._entries[key] = ThrottleEntry(
                job_name=alert.job_name,
                alert_kind=alert.kind,
                first_sent_at=now,
                last_sent_at=now,
            )
        else:
            existing.last_sent_at = now
            existing.send_count += 1

    def reset(self, job_name: str, alert_kind: str) -> None:
        """Clear throttle state for a specific (job, kind) pair."""
        self._entries.pop((job_name, alert_kind), None)

    def reset_all(self) -> None:
        """Clear all throttle state."""
        self._entries.clear()

    def entry_for(self, job_name: str, alert_kind: str) -> Optional[ThrottleEntry]:
        return self._entries.get((job_name, alert_kind))
