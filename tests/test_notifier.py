"""Tests for cronwatcher.notifier."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerting import Alert
from cronwatcher.notifier import (
    EmailNotifier,
    LogNotifier,
    WebhookNotifier,
    build_notifier,
)


@pytest.fixture()
def sample_alert() -> Alert:
    return Alert(
        job_name="backup",
        alert_type="overdue",
        message="Job 'backup' has not run in 7200s (limit 3600s)",
        last_seen=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestLogNotifier:
    def test_send_returns_true(self, sample_alert: Alert) -> None:
        notifier = LogNotifier()
        assert notifier.send(sample_alert) is True

    def test_send_logs_at_configured_level(self, sample_alert: Alert, caplog) -> None:
        notifier = LogNotifier(level=logging.ERROR)
        with caplog.at_level(logging.ERROR, logger="cronwatcher.notifier"):
            notifier.send(sample_alert)
        assert "backup" in caplog.text
        assert "overdue" in caplog.text

    def test_default_level_is_warning(self) -> None:
        notifier = LogNotifier()
        assert notifier.level == logging.WARNING


class TestEmailNotifier:
    def _make_notifier(self) -> EmailNotifier:
        return EmailNotifier(
            smtp_host="localhost",
            smtp_port=25,
            sender="alerts@example.com",
            recipients=["ops@example.com"],
        )

    def test_send_success(self, sample_alert: Alert) -> None:
        notifier = self._make_notifier()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("smtplib.SMTP", return_value=mock_smtp):
            result = notifier.send(sample_alert)

        assert result is True
        mock_smtp.sendmail.assert_called_once()

    def test_send_failure_returns_false(self, sample_alert: Alert) -> None:
        notifier = self._make_notifier()
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
            result = notifier.send(sample_alert)
        assert result is False


class TestWebhookNotifier:
    def test_send_success(self, sample_alert: Alert) -> None:
        notifier = WebhookNotifier(url="http://hooks.example.com/alert")
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = notifier.send(sample_alert)

        assert result is True

    def test_send_failure_returns_false(self, sample_alert: Alert) -> None:
        notifier = WebhookNotifier(url="http://hooks.example.com/alert")
        with patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
            result = notifier.send(sample_alert)
        assert result is False


class TestBuildNotifier:
    def test_build_log_notifier(self) -> None:
        n = build_notifier({"type": "log", "level": "error"})
        assert isinstance(n, LogNotifier)
        assert n.level == logging.ERROR

    def test_build_email_notifier(self) -> None:
        cfg = {
            "type": "email",
            "smtp_host": "mail.example.com",
            "smtp_port": "587",
            "sender": "a@b.com",
            "recipients": ["x@y.com"],
        }
        n = build_notifier(cfg)
        assert isinstance(n, EmailNotifier)
        assert n.smtp_port == 587

    def test_build_webhook_notifier(self) -> None:
        n = build_notifier({"type": "webhook", "url": "http://example.com"})
        assert isinstance(n, WebhookNotifier)
        assert n.url == "http://example.com"

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown notifier type"):
            build_notifier({"type": "slack"})
