"""High-level helper: run alert dispatch and log a summary."""

from __future__ import annotations

import logging
from typing import List, Optional

from cronwatcher.alerting import Alert, AlertManager
from cronwatcher.webhook_dispatcher import DispatchResult, WebhookDispatcher

logger = logging.getLogger(__name__)


class DispatchRunner:
    """Collect pending alerts from AlertManager and dispatch via WebhookDispatcher."""

    def __init__(
        self,
        alert_manager: AlertManager,
        dispatcher: WebhookDispatcher,
    ) -> None:
        self._alert_manager = alert_manager
        self._dispatcher = dispatcher

    def run(self, alerts: Optional[List[Alert]] = None) -> List[DispatchResult]:
        """Dispatch *alerts* (or all pending alerts) and return results.

        If *alerts* is None the runner will pull from ``alert_manager.pending``
        when that attribute is available, otherwise it dispatches nothing.
        """
        if alerts is None:
            alerts = list(getattr(self._alert_manager, "pending", []))

        if not alerts:
            logger.debug("DispatchRunner: no alerts to dispatch.")
            return []

        results = self._dispatcher.dispatch_all(alerts)
        self._log_results(results)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_results(self, results: List[DispatchResult]) -> None:
        for r in results:
            if r.all_succeeded:
                logger.info(
                    "Dispatched alert for %r to %d webhook(s).",
                    r.job_name,
                    r.total,
                )
            else:
                logger.warning(
                    "Dispatch for %r had %d failure(s) out of %d. Errors: %s",
                    r.job_name,
                    r.failed,
                    r.total,
                    r.errors,
                )
