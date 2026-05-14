"""WebhookDispatcher: fan-out alerts to multiple WebhookNotifier endpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cronwatcher.alerting import Alert
from cronwatcher.webhook_notifier import WebhookNotifier

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """Summary of a single fan-out dispatch attempt."""

    total: int
    succeeded: int
    failed: int
    failures: List[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0

    def __repr__(self) -> str:
        return (
            f"DispatchResult(total={self.total}, succeeded={self.succeeded}, "
            f"failed={self.failed})"
        )


class WebhookDispatcher:
    """Sends an alert to every registered WebhookNotifier and collects results."""

    def __init__(self, notifiers: List[WebhookNotifier] | None = None) -> None:
        self._notifiers: List[WebhookNotifier] = list(notifiers or [])

    def add(self, notifier: WebhookNotifier) -> None:
        """Register an additional notifier."""
        self._notifiers.append(notifier)

    def dispatch(self, alert: Alert) -> DispatchResult:
        """Send *alert* to all registered notifiers.

        Returns a :class:`DispatchResult` summarising successes and failures.
        """
        total = len(self._notifiers)
        succeeded = 0
        failures: List[str] = []

        for notifier in self._notifiers:
            try:
                ok = notifier.send(alert)
            except Exception as exc:
                ok = False
                logger.exception(
                    "Unhandled error dispatching to %s: %s", notifier.url, exc
                )

            if ok:
                succeeded += 1
            else:
                failures.append(notifier.url)
                logger.warning(
                    "Webhook dispatch failed for job '%s' → %s",
                    alert.job_name,
                    notifier.url,
                )

        result = DispatchResult(
            total=total,
            succeeded=succeeded,
            failed=len(failures),
            failures=failures,
        )
        logger.debug("Dispatch result: %r", result)
        return result
