"""Tests for cronwatcher.silence_detector."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.heartbeat import HeartbeatTracker, JobRecord
from cronwatcher.alerting import AlertManager
from cronwatcher.silence_detector import SilenceDetector, SilenceReport


@pytest.fixture
def tracker():
    t = HeartbeatTracker()
    t.register("nightly_backup", expected_interval_seconds=3600)
    t.register("health_ping", expected_interval_seconds=60)
    return t


@pytest.fixture
def alert_manager():
    return MagicMock(spec=AlertManager)


@pytest.fixture
def detector(tracker, alert_manager):
    return SilenceDetector(tracker, alert_manager, multiplier=2.0)


class TestSilenceReport:
    def test_silence_duration_when_never_seen(self):
        now = datetime.now(timezone.utc)
        report = SilenceReport(
            job_name="job",
            last_seen=None,
            silence_threshold_seconds=120.0,
            detected_at=now,
        )
        assert report.silence_duration_seconds is None

    def test_silence_duration_calculated(self):
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(seconds=300)
        report = SilenceReport(
            job_name="job",
            last_seen=last_seen,
            silence_threshold_seconds=120.0,
            detected_at=now,
        )
        assert abs(report.silence_duration_seconds - 300.0) < 1.0

    def test_repr_never_seen(self):
        report = SilenceReport(
            job_name="my_job",
            last_seen=None,
            silence_threshold_seconds=60.0,
        )
        assert "never seen" in repr(report)
        assert "my_job" in repr(report)

    def test_repr_with_last_seen(self):
        now = datetime.now(timezone.utc)
        report = SilenceReport(
            job_name="my_job",
            last_seen=now - timedelta(seconds=90),
            silence_threshold_seconds=60.0,
            detected_at=now,
        )
        assert "90" in repr(report) or "s" in repr(report)


class TestSilenceDetector:
    def test_no_reports_when_jobs_on_time(self, tracker, detector):
        now = datetime.now(timezone.utc)
        tracker.record_execution("nightly_backup", at=now - timedelta(seconds=100))
        tracker.record_execution("health_ping", at=now - timedelta(seconds=10))
        reports = detector.check_all()
        assert reports == []

    def test_detects_overdue_job(self, tracker, detector):
        now = datetime.now(timezone.utc)
        tracker.record_execution(
            "nightly_backup", at=now - timedelta(seconds=8000)
        )
        reports = detector.check_all()
        job_names = [r.job_name for r in reports]
        assert "nightly_backup" in job_names

    def test_never_seen_job_is_reported(self, tracker, detector):
        reports = detector.check_all()
        job_names = [r.job_name for r in reports]
        assert "nightly_backup" in job_names
        assert "health_ping" in job_names

    def test_alert_triggered_on_silence(self, tracker, alert_manager, detector):
        reports = detector.check_all()
        assert alert_manager.trigger.called

    def test_alert_not_duplicated_within_window(self, tracker, alert_manager, detector):
        detector.check_all()
        first_call_count = alert_manager.trigger.call_count
        detector.check_all()
        assert alert_manager.trigger.call_count == first_call_count

    def test_threshold_uses_multiplier(self, tracker, alert_manager):
        detector = SilenceDetector(tracker, alert_manager, multiplier=3.0)
        now = datetime.now(timezone.utc)
        # health_ping interval=60, multiplier=3 → threshold=180s; 150s should be fine
        tracker.record_execution("health_ping", at=now - timedelta(seconds=150))
        reports = detector.check_all()
        job_names = [r.job_name for r in reports]
        assert "health_ping" not in job_names
