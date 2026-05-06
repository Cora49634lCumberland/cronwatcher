"""Tests for DriftMonitor integration."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.drift_monitor import DriftMonitor
from cronwatcher.heartbeat import HeartbeatTracker, JobRecord
from cronwatcher.alerting import AlertManager
from cronwatcher.scheduler import CronSchedule


UTC = timezone.utc
NOW = datetime(2024, 1, 15, 12, 5, 0, tzinfo=UTC)


@pytest.fixture
def heartbeat():
    return HeartbeatTracker()


@pytest.fixture
def alert_manager():
    mgr = MagicMock(spec=AlertManager)
    return mgr


@pytest.fixture
def schedule():
    return CronSchedule(expression="* * * * *", job_name="test_job", grace_seconds=10.0)


@pytest.fixture
def monitor(heartbeat, alert_manager):
    return DriftMonitor(
        heartbeat=heartbeat,
        alert_manager=alert_manager,
        threshold_seconds=30.0,
    )


class TestDriftMonitor:
    def test_returns_none_when_job_never_seen(self, monitor, schedule):
        result = monitor.check_job("test_job", schedule, now=NOW)
        assert result is None

    def test_returns_drift_record_when_job_seen(self, monitor, heartbeat, schedule):
        last_seen = NOW - timedelta(seconds=10)
        heartbeat._jobs["test_job"] = JobRecord(job_name="test_job", last_seen=last_seen)
        result = monitor.check_job("test_job", schedule, now=NOW)
        assert result is not None
        assert result.job_name == "test_job"

    def test_no_alert_when_drift_within_threshold(self, monitor, heartbeat, alert_manager, schedule):
        last_seen = NOW - timedelta(seconds=5)
        heartbeat._jobs["test_job"] = JobRecord(job_name="test_job", last_seen=last_seen)
        monitor.check_job("test_job", schedule, now=NOW)
        alert_manager.emit.assert_not_called()

    def test_alert_emitted_when_drift_exceeds_threshold(self, monitor, heartbeat, alert_manager, schedule):
        last_seen = NOW - timedelta(seconds=120)
        heartbeat._jobs["test_job"] = JobRecord(job_name="test_job", last_seen=last_seen)
        monitor.check_job("test_job", schedule, now=NOW)
        alert_manager.emit.assert_called_once()
        alert_arg = alert_manager.emit.call_args[0][0]
        assert alert_arg.job_name == "test_job"
        assert "drift" in alert_arg.reason

    def test_uses_current_time_when_now_not_provided(self, monitor, heartbeat, schedule):
        last_seen = datetime.now(tz=UTC) - timedelta(seconds=5)
        heartbeat._jobs["test_job"] = JobRecord(job_name="test_job", last_seen=last_seen)
        result = monitor.check_job("test_job", schedule)
        assert result is not None
