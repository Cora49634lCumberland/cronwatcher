"""Tests for cronwatcher.heartbeat module."""

import time
import pytest
from unittest.mock import patch

from cronwatcher.heartbeat import HeartbeatTracker, JobRecord


FAKE_NOW = 1_700_000_000.0


@pytest.fixture()
def tracker() -> HeartbeatTracker:
    return HeartbeatTracker()


class TestJobRecord:
    def test_record_execution_sets_last_seen(self):
        record = JobRecord(name="test", expected_interval_seconds=300)
        with patch("cronwatcher.heartbeat.time.time", return_value=FAKE_NOW):
            record.record_execution()
        assert record.last_seen == FAKE_NOW

    def test_not_overdue_when_never_seen(self):
        record = JobRecord(name="test", expected_interval_seconds=60)
        assert record.is_overdue() is False

    def test_not_overdue_within_interval(self):
        record = JobRecord(name="test", expected_interval_seconds=300)
        record.last_seen = time.time() - 100  # well within interval
        assert record.is_overdue() is False

    def test_overdue_when_past_interval(self):
        record = JobRecord(name="test", expected_interval_seconds=60)
        record.last_seen = time.time() - 200  # clearly overdue
        assert record.is_overdue() is True

    def test_grace_period_delays_overdue(self):
        record = JobRecord(name="test", expected_interval_seconds=60)
        record.last_seen = time.time() - 80  # overdue without grace
        assert record.is_overdue(grace_period_seconds=0) is True
        assert record.is_overdue(grace_period_seconds=60) is False

    def test_drift_warning_logged(self, caplog):
        record = JobRecord(name="slow_job", expected_interval_seconds=300,
                           drift_threshold_seconds=30)
        record.last_seen = FAKE_NOW - 500  # 200s drift
        with patch("cronwatcher.heartbeat.time.time", return_value=FAKE_NOW):
            import logging
            with caplog.at_level(logging.WARNING, logger="cronwatcher.heartbeat"):
                record.record_execution()
        assert "Drift detected" in caplog.text
        assert "slow_job" in caplog.text

    def test_missed_count_resets_on_ping(self):
        record = JobRecord(name="test", expected_interval_seconds=60)
        record.missed_count = 5
        with patch("cronwatcher.heartbeat.time.time", return_value=FAKE_NOW):
            record.record_execution()
        assert record.missed_count == 0


class TestHeartbeatTracker:
    def test_register_and_ping(self, tracker):
        tracker.register("backup", expected_interval_seconds=3600)
        with patch("cronwatcher.heartbeat.time.time", return_value=FAKE_NOW):
            tracker.ping("backup")
        assert tracker.get_record("backup").last_seen == FAKE_NOW

    def test_duplicate_registration_raises(self, tracker):
        tracker.register("job", 60)
        with pytest.raises(ValueError, match="already registered"):
            tracker.register("job", 120)

    def test_ping_unknown_job_raises(self, tracker):
        with pytest.raises(KeyError, match="Unknown job"):
            tracker.ping("nonexistent")

    def test_check_all_returns_overdue_status(self, tracker):
        tracker.register("fast_job", expected_interval_seconds=10)
        record = tracker.get_record("fast_job")
        record.last_seen = time.time() - 300  # definitely overdue
        results = tracker.check_all(grace_period_seconds=0)
        assert results["fast_job"] is True

    def test_check_all_increments_missed_count(self, tracker):
        tracker.register("silent_job", expected_interval_seconds=10)
        record = tracker.get_record("silent_job")
        record.last_seen = time.time() - 300
        tracker.check_all(grace_period_seconds=0)
        tracker.check_all(grace_period_seconds=0)
        assert record.missed_count == 2

    def test_get_record_unknown_raises(self, tracker):
        with pytest.raises(KeyError):
            tracker.get_record("ghost")
