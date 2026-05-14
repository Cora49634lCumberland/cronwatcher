"""Tests for WebhookNotifier."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerting import Alert
from cronwatcher.webhook_notifier import WebhookNotifier


@pytest.fixture
def alert() -> Alert:
    return Alert(
        job_name="nightly-backup",
        reason="overdue",
        severity="critical",
        last_seen=datetime(2024, 6, 1, 2, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def notifier() -> WebhookNotifier:
    return WebhookNotifier(url="https://hooks.example.com/cronwatcher")


class TestWebhookNotifier:
    def test_send_returns_true_on_200(self, notifier, alert):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = notifier.send(alert)

        assert result is True
        assert notifier._last_status_code == 200

    def test_send_returns_false_on_500(self, notifier, alert):
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="", code=500, msg="Server Error", hdrs=None, fp=None
            ),
        ):
            result = notifier.send(alert)

        assert result is False
        assert notifier._last_status_code == 500

    def test_send_returns_false_on_network_error(self, notifier, alert):
        with patch(
            "urllib.request.urlopen", side_effect=OSError("connection refused")
        ):
            result = notifier.send(alert)

        assert result is False
        assert notifier._last_status_code is None

    def test_payload_contains_expected_fields(self, notifier, alert):
        captured: list = []

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req, timeout):
            captured.append(json.loads(req.data.decode()))
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            notifier.send(alert)

        payload = captured[0]
        assert payload["job_name"] == "nightly-backup"
        assert payload["reason"] == "overdue"
        assert payload["severity"] == "critical"
        assert payload["last_seen"] == "2024-06-01T02:00:00+00:00"

    def test_payload_last_seen_none_when_never_seen(self, notifier):
        alert_no_seen = Alert(
            job_name="orphan-job",
            reason="never ran",
            severity="warning",
            last_seen=None,
        )
        captured: list = []

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req, timeout):
            captured.append(json.loads(req.data.decode()))
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            notifier.send(alert_no_seen)

        assert captured[0]["last_seen"] is None

    def test_extra_headers_are_forwarded(self, alert):
        notifier_with_auth = WebhookNotifier(
            url="https://hooks.example.com/secure",
            extra_headers={"Authorization": "Bearer token123"},
        )
        captured_req: list = []

        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req, timeout):
            captured_req.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = notifier_with_auth.send(alert)

        assert result is True
        assert captured_req[0].get_header("Authorization") == "Bearer token123"
