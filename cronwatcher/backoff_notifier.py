"""BackoffNotifier: wraps a notifier and suppresses repeated alerts using exponential backoff."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatcher.alerting import Alert
from cronwatcher.notifier import NotifierBase


@dataclass
class BackoffState:
    """Tracks suppression state for a single alert key."""
    attempt: int = 0
    last_sent_at: Optional[float] = None
    next_allowed_at: float = 0.0

    def record_sent(self, base_delay: float, max_delay: float) -> None:
        self.last_sent_at = time.time()
        delay = min(base_delay * (2 ** self.attempt), max_delay)
        self.next_allowed_at = self.last_sent_at + delay
        self.attempt += 1

    def is_suppressed(self) -> bool:
        return time.time() < self.next_allowed_at

    def reset(self) -> None:
        self.attempt = 0
        self.last_sent_at = None
        self.next_allowed_at = 0.0


class BackoffNotifier:
    """Decorator around a NotifierBase that applies exponential backoff per alert key.

    Alerts for the same job+kind are suppressed until the backoff window expires.
    """

    def __init__(
        self,
        notifier: NotifierBase,
        base_delay: float = 60.0,
        max_delay: float = 3600.0,
    ) -> None:
        self._notifier = notifier
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._states: Dict[str, BackoffState] = {}

    def _key(self, alert: Alert) -> str:
        return f"{alert.job_name}:{alert.kind}"

    def _get_state(self, key: str) -> BackoffState:
        if key not in self._states:
            self._states[key] = BackoffState()
        return self._states[key]

    def send(self, alert: Alert) -> bool:
        """Send the alert if not suppressed; returns True if the alert was delivered."""
        key = self._key(alert)
        state = self._get_state(key)

        if state.is_suppressed():
            return False

        delivered = self._notifier.send(alert)
        if delivered:
            state.record_sent(self._base_delay, self._max_delay)
        return delivered

    def reset(self, job_name: str, kind: str) -> None:
        """Reset backoff state for a job+kind pair (e.g. after recovery)."""
        key = f"{job_name}:{kind}"
        if key in self._states:
            self._states[key].reset()

    def suppressed_keys(self) -> list:
        return [k for k, s in self._states.items() if s.is_suppressed()]
