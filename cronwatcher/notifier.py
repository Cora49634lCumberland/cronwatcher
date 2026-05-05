"""Notification backends for cronwatcher alerts."""

from __future__ import annotations

import logging
import smtplib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import List

from cronwatcher.alerting import Alert

logger = logging.getLogger(__name__)


class NotifierBase(ABC):
    """Abstract base class for alert notifiers."""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Send an alert. Returns True on success."""
        ...


@dataclass
class LogNotifier(NotifierBase):
    """Writes alerts to the Python logging system."""

    level: int = logging.WARNING

    def send(self, alert: Alert) -> bool:
        logger.log(self.level, "[cronwatcher] %s", alert)
        return True


@dataclass
class EmailNotifier(NotifierBase):
    """Sends alerts via SMTP."""

    smtp_host: str
    smtp_port: int
    sender: str
    recipients: List[str]
    subject_prefix: str = "[cronwatcher]"
    timeout: int = 10

    def send(self, alert: Alert) -> bool:
        subject = f"{self.subject_prefix} {alert.alert_type}: {alert.job_name}"
        body = str(alert)
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                server.sendmail(self.sender, self.recipients, msg.as_string())
            logger.debug("Email alert sent for job '%s'", alert.job_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send email alert for '%s': %s", alert.job_name, exc)
            return False


@dataclass
class WebhookNotifier(NotifierBase):
    """Posts alerts to an HTTP webhook endpoint."""

    url: str
    headers: dict = field(default_factory=dict)
    timeout: int = 10

    def send(self, alert: Alert) -> bool:
        try:
            import urllib.request

            payload = json.dumps({
                "job_name": alert.job_name,
                "alert_type": alert.alert_type,
                "message": str(alert),
            }).encode()

            req = urllib.request.Request(
                self.url,
                data=payload,
                headers={"Content-Type": "application/json", **self.headers},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                logger.debug(
                    "Webhook alert sent for '%s', status=%s", alert.job_name, resp.status
                )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Webhook alert failed for '%s': %s", alert.job_name, exc)
            return False


def build_notifier(config: dict) -> NotifierBase:
    """Factory: build a notifier from a config dict."""
    kind = config.get("type", "log")
    if kind == "log":
        return LogNotifier(level=getattr(logging, config.get("level", "WARNING").upper()))
    if kind == "email":
        return EmailNotifier(
            smtp_host=config["smtp_host"],
            smtp_port=int(config.get("smtp_port", 25)),
            sender=config["sender"],
            recipients=config["recipients"],
            subject_prefix=config.get("subject_prefix", "[cronwatcher]"),
        )
    if kind == "webhook":
        return WebhookNotifier(
            url=config["url"],
            headers=config.get("headers", {}),
            timeout=int(config.get("timeout", 10)),
        )
    raise ValueError(f"Unknown notifier type: {kind!r}")
