"""Tests for DriftRecord and DriftAnalyzer."""

from datetime import datetime, timezone, timedelta

import pytest

from cronwatcher.drift import DriftRecord, DriftAnalyzer


UTC = timezone.utc
NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def analyzer():
    return DriftAnalyzer(threshold_seconds=60.0)


class TestDriftRecord:
    def test_drift_seconds_late(self):
        expected = NOW
        actual = NOW + timedelta(seconds=90)
        record = DriftRecord(job_name="job", expected_at=expected, actual_at=actual)
        assert record.drift_seconds == pytest.approx(90.0)

    def test_drift_seconds_early(self):
        expected = NOW
        actual = NOW - timedelta(seconds=30)
        record = DriftRecord(job_name="job", expected_at=expected, actual_at=actual)
        assert record.drift_seconds == pytest.approx(-30.0)

    def test_is_late_true(self):
        record = DriftRecord(job_name="j", expected_at=NOW, actual_at=NOW + timedelta(seconds=5))
        assert record.is_late is True

    def test_is_late_false_when_early(self):
        record = DriftRecord(job_name="j", expected_at=NOW, actual_at=NOW - timedelta(seconds=5))
        assert record.is_late is False

    def test_repr_contains_job_name(self):
        record = DriftRecord(job_name="myjob", expected_at=NOW, actual_at=NOW + timedelta(seconds=10))
        assert "myjob" in repr(record)


class TestDriftAnalyzer:
    def test_record_stores_history(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=10))
        assert len(analyzer.history["job1"]) == 1

    def test_is_drifting_below_threshold(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=30))
        assert analyzer.is_drifting("job1") is False

    def test_is_drifting_above_threshold(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=120))
        assert analyzer.is_drifting("job1") is True

    def test_is_drifting_no_history(self, analyzer):
        assert analyzer.is_drifting("unknown") is False

    def test_average_drift_single(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=40))
        assert analyzer.average_drift("job1") == pytest.approx(40.0)

    def test_average_drift_multiple(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=20))
        analyzer.record("job1", NOW, NOW + timedelta(seconds=60))
        assert analyzer.average_drift("job1") == pytest.approx(40.0)

    def test_average_drift_no_history(self, analyzer):
        assert analyzer.average_drift("missing") is None

    def test_clear_history(self, analyzer):
        analyzer.record("job1", NOW, NOW + timedelta(seconds=10))
        analyzer.clear_history("job1")
        assert "job1" not in analyzer.history
