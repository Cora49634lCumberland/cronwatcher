"""Tests for RecoveryDetector."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.alerting import AlertManager
from cronwatcher.recovery_detector import RecoveryDetector, RecoveryEvent


INTERVAL = 60.0  # seconds


@pytest.fixture()
def tracker():
    return HeartbeatTracker()


@pytest.fixture()
def alert_manager():
    mgr = AlertManager(tracker=HeartbeatTracker())
    mgr.emit = MagicMock()
    return mgr


@pytest.fixture()
def detector(tracker, alert_manager):
    return RecoveryDetector(tracker=tracker, alert_manager=alert_manager)


class TestRecoveryDetector:
    def test_no_event_for_unknown_job(self, detector):
        result = detector.check_job("missing_job", INTERVAL)
        assert result is None

    def test_no_event_when_job_healthy_and_never_overdue(self, tracker, detector):
        tracker.record_execution("my_job")
        result = detector.check_job("my_job", INTERVAL)
        assert result is None

    def test_no_recovery_event_when_still_overdue(self, tracker, detector):
        old_time = datetime.utcnow() - timedelta(seconds=200)
        tracker.record_execution("slow_job")
        tracker._records["slow_job"].last_seen = old_time

        result = detector.check_job("slow_job", INTERVAL)
        assert result is None
        assert "slow_job" in detector.overdue_jobs

    def test_recovery_event_emitted_after_overdue(self, tracker, detector, alert_manager):
        old_time = datetime.utcnow() - timedelta(seconds=200)
        tracker.record_execution("flaky_job")
        tracker._records["flaky_job"].last_seen = old_time

        # First check — job is overdue
        detector.check_job("flaky_job", INTERVAL)
        assert "flaky_job" in detector.overdue_jobs

        # Job recovers
        tracker.record_execution("flaky_job")

        event = detector.check_job("flaky_job", INTERVAL)

        assert isinstance(event, RecoveryEvent)
        assert event.job_name == "flaky_job"
        assert event.silent_since is not None
        assert "flaky_job" not in detector.overdue_jobs
        alert_manager.emit.assert_called_once()

    def test_recovery_alert_contains_job_name(self, tracker, detector, alert_manager):
        old_time = datetime.utcnow() - timedelta(seconds=200)
        tracker.record_execution("important_job")
        tracker._records["important_job"].last_seen = old_time

        detector.check_job("important_job", INTERVAL)
        tracker.record_execution("important_job")
        detector.check_job("important_job", INTERVAL)

        alert = alert_manager.emit.call_args[0][0]
        assert "important_job" in alert.message
        assert alert.severity == "info"

    def test_overdue_jobs_list(self, tracker, detector):
        for name in ("job_a", "job_b"):
            tracker.record_execution(name)
            tracker._records[name].last_seen = datetime.utcnow() - timedelta(seconds=200)
            detector.check_job(name, INTERVAL)

        assert set(detector.overdue_jobs) == {"job_a", "job_b"}

    def test_repr_recovery_event(self):
        now = datetime.utcnow()
        event = RecoveryEvent(job_name="x", recovered_at=now, silent_since=now)
        assert "x" in repr(event)
        assert "was silent since" in repr(event)
