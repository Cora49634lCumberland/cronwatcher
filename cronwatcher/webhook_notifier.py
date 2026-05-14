"""Webhook notifier: sends alerts via HTTP POST to a configured endpoint."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cronwatcher.alerting import Alert
from cronwatcher.notifier import NotifierBase

logger = logging.getLogger(__name__)


@dataclass
class WebhookNotifier(NotifierBase):
    """Sends alert payloads as JSON to an HTTP/HTTPS webhook URL."""

    url: str
    timeout: int = 10
    extra_headers: Dict[str, str] = field(default_factory=dict)
    _last_status_code: Optional[int] = field(default=None, init=False, repr=False)

    def _build_payload(self, alert: Alert) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "job_name": alert.job_name,
            "reason": alert.reason,
            "severity": alert.severity,
        }
        if alert.last_seen is not None:
            payload["last_seen"] = alert.last_seen.isoformat()
        else:
            payload["last_seen"] = None
        return payload

    def send(self, alert: Alert) -> bool:
        payload = self._build_payload(alert)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        headers.update(self.extra_headers)

        req = urllib.request.Request(
            self.url, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self._last_status_code = resp.status
                logger.debug(
                    "Webhook delivered alert for '%s' → HTTP %d",
                    alert.job_name,
                    resp.status,
                )
                return 200 <= resp.status < 300
        except urllib.error.HTTPError as exc:
            self._last_status_code = exc.code
            logger.warning(
                "Webhook HTTP error for '%s': %s", alert.job_name, exc
            )
            return False
        except Exception as exc:  # network errors, timeouts, etc.
            self._last_status_code = None
            logger.error(
                "Webhook delivery failed for '%s': %s", alert.job_name, exc
            )
            return False
