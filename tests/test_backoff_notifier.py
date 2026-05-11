"""Tests for BackoffNotifier."""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerting import Alert
from cronwatcher.backoff_notifier import BackoffNotifier, BackoffState


@pytest.fixture
def alert():
    return Alert(
        job_name="backup",
        kind="overdue",
        message="Job has not run",
        last_seen=None,
    )


@pytest.fixture
def mock_notifier():
    n = MagicMock()
    n.send.return_value = True
    return n


@pytest.fixture
def notifier(mock_notifier):
    return BackoffNotifier(mock_notifier, base_delay=10.0, max_delay=100.0)


class TestBackoffState:
    def test_not_suppressed_initially(self):
        state = BackoffState()
        assert not state.is_suppressed()

    def test_suppressed_after_record_sent(self):
        state = BackoffState()
        state.record_sent(base_delay=60.0, max_delay=3600.0)
        assert state.is_suppressed()

    def test_reset_clears_suppression(self):
        state = BackoffState()
        state.record_sent(base_delay=60.0, max_delay=3600.0)
        state.reset()
        assert not state.is_suppressed()
        assert state.attempt == 0

    def test_delay_doubles_each_attempt(self):
        state = BackoffState()
        now = time.time()
        state.record_sent(base_delay=10.0, max_delay=1000.0)  # attempt 0 -> delay 10
        first_next = state.next_allowed_at
        state.record_sent(base_delay=10.0, max_delay=1000.0)  # attempt 1 -> delay 20
        second_next = state.next_allowed_at
        assert second_next > first_next

    def test_delay_capped_at_max(self):
        state = BackoffState()
        state.attempt = 20
        state.record_sent(base_delay=10.0, max_delay=50.0)
        assert state.next_allowed_at <= time.time() + 51.0


class TestBackoffNotifier:
    def test_first_alert_is_delivered(self, notifier, mock_notifier, alert):
        result = notifier.send(alert)
        assert result is True
        mock_notifier.send.assert_called_once_with(alert)

    def test_second_alert_is_suppressed(self, notifier, mock_notifier, alert):
        notifier.send(alert)
        result = notifier.send(alert)
        assert result is False
        assert mock_notifier.send.call_count == 1

    def test_different_kind_not_suppressed(self, notifier, mock_notifier, alert):
        notifier.send(alert)
        alert2 = Alert(job_name="backup", kind="drift", message="Late", last_seen=None)
        result = notifier.send(alert2)
        assert result is True

    def test_reset_allows_resend(self, notifier, mock_notifier, alert):
        notifier.send(alert)
        notifier.reset("backup", "overdue")
        result = notifier.send(alert)
        assert result is True
        assert mock_notifier.send.call_count == 2

    def test_suppressed_keys_lists_active(self, notifier, alert):
        notifier.send(alert)
        keys = notifier.suppressed_keys()
        assert "backup:overdue" in keys

    def test_no_delivery_when_notifier_fails(self, alert):
        failing = MagicMock()
        failing.send.return_value = False
        bn = BackoffNotifier(failing, base_delay=10.0, max_delay=100.0)
        result = bn.send(alert)
        assert result is False
        # State should not advance since delivery failed
        assert not bn._states["backup:overdue"].is_suppressed()
