"""Tests for WebhookDispatcher."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerting import Alert
from cronwatcher.webhook_dispatcher import DispatchResult, WebhookDispatcher
from cronwatcher.webhook_notifier import WebhookNotifier


@pytest.fixture()
def alert() -> Alert:
    return Alert(
        job_name="backup",
        message="Job is overdue",
        last_seen=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def notifier_ok() -> WebhookNotifier:
    n = WebhookNotifier(url="https://hooks.example.com/ok")
    n.send = MagicMock(return_value=True)
    return n


@pytest.fixture()
def notifier_fail() -> WebhookNotifier:
    n = WebhookNotifier(url="https://hooks.example.com/fail")
    n.send = MagicMock(return_value=False)
    return n


@pytest.fixture()
def dispatcher(notifier_ok) -> WebhookDispatcher:
    return WebhookDispatcher(notifiers=[notifier_ok])


class TestDispatchResult:
    def test_all_succeeded_true(self):
        r = DispatchResult(job_name="j", total=2, succeeded=2, failed=0)
        assert r.all_succeeded is True

    def test_all_succeeded_false_when_any_failed(self):
        r = DispatchResult(job_name="j", total=2, succeeded=1, failed=1)
        assert r.all_succeeded is False

    def test_all_succeeded_false_when_no_notifiers(self):
        r = DispatchResult(job_name="j", total=0, succeeded=0, failed=0)
        assert r.all_succeeded is False

    def test_repr_contains_job_name(self):
        r = DispatchResult(job_name="myjob", total=3, succeeded=3, failed=0)
        assert "myjob" in repr(r)
        assert "3/3" in repr(r)


class TestWebhookDispatcher:
    def test_dispatch_single_ok(self, dispatcher, alert, notifier_ok):
        result = dispatcher.dispatch(alert)
        assert result.succeeded == 1
        assert result.failed == 0
        assert result.all_succeeded
        notifier_ok.send.assert_called_once_with(alert)

    def test_dispatch_single_fail(self, notifier_fail, alert):
        d = WebhookDispatcher(notifiers=[notifier_fail])
        result = d.dispatch(alert)
        assert result.succeeded == 0
        assert result.failed == 1
        assert not result.all_succeeded

    def test_dispatch_mixed(self, notifier_ok, notifier_fail, alert):
        d = WebhookDispatcher(notifiers=[notifier_ok, notifier_fail])
        result = d.dispatch(alert)
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.total == 2

    def test_dispatch_exception_counts_as_failure(self, alert):
        notifier = WebhookNotifier(url="https://hooks.example.com/boom")
        notifier.send = MagicMock(side_effect=RuntimeError("timeout"))
        d = WebhookDispatcher(notifiers=[notifier])
        result = d.dispatch(alert)
        assert result.failed == 1
        assert any("timeout" in e for e in result.errors)

    def test_dispatch_empty_notifiers(self, alert):
        d = WebhookDispatcher(notifiers=[])
        result = d.dispatch(alert)
        assert result.total == 0
        assert not result.all_succeeded

    def test_dispatch_all_returns_one_result_per_alert(self, dispatcher):
        alerts = [
            Alert(job_name="a", message="m1"),
            Alert(job_name="b", message="m2"),
        ]
        results = dispatcher.dispatch_all(alerts)
        assert len(results) == 2
        assert results[0].job_name == "a"
        assert results[1].job_name == "b"

    def test_add_notifier_increases_total(self, dispatcher, alert, notifier_fail):
        dispatcher.add_notifier(notifier_fail)
        result = dispatcher.dispatch(alert)
        assert result.total == 2
