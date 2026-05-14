"""Dispatch alerts to multiple webhook notifiers and collect results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronwatcher.alerting import Alert
from cronwatcher.webhook_notifier import WebhookNotifier


@dataclass
class DispatchResult:
    job_name: str
    total: int
    succeeded: int
    failed: int
    errors: List[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0 and self.total > 0

    def __repr__(self) -> str:
        return (
            f"DispatchResult(job={self.job_name!r}, "
            f"succeeded={self.succeeded}/{self.total})"
        )


class WebhookDispatcher:
    """Send an alert to every registered WebhookNotifier and aggregate results."""

    def __init__(self, notifiers: List[WebhookNotifier]) -> None:
        self._notifiers = list(notifiers)

    def add_notifier(self, notifier: WebhookNotifier) -> None:
        self._notifiers.append(notifier)

    def dispatch(self, alert: Alert) -> DispatchResult:
        succeeded = 0
        failed = 0
        errors: List[str] = []

        for notifier in self._notifiers:
            try:
                ok = notifier.send(alert)
            except Exception as exc:  # noqa: BLE001
                ok = False
                errors.append(f"{notifier.url}: {exc}")

            if ok:
                succeeded += 1
            else:
                failed += 1
                if not errors or errors[-1].startswith(notifier.url):
                    pass  # error already recorded above
                else:
                    errors.append(f"{notifier.url}: returned failure")

        return DispatchResult(
            job_name=alert.job_name,
            total=len(self._notifiers),
            succeeded=succeeded,
            failed=failed,
            errors=errors,
        )

    def dispatch_all(self, alerts: List[Alert]) -> List[DispatchResult]:
        return [self.dispatch(a) for a in alerts]
