"""Tests for HistoryReporter and JobSummary."""

import pytest
from unittest.mock import MagicMock
from cronwatcher.history import ExecutionEvent
from cronwatcher.history_reporter import HistoryReporter, JobSummary


def make_event(status: str, duration: float = 1.0, ts: str = "2024-01-01T00:00:00") -> ExecutionEvent:
    return ExecutionEvent(job_name="test_job", executed_at=ts, status=status, duration_seconds=duration)


@pytest.fixture
def history():
    mock = MagicMock()
    mock.known_jobs.return_value = ["test_job"]
    return mock


@pytest.fixture
def reporter(history):
    return HistoryReporter(history)


class TestJobSummary:
    def test_str_with_data(self):
        summary = JobSummary(
            job_name="backup",
            total_runs=5,
            successful_runs=4,
            failed_runs=1,
            avg_duration_seconds=2.5,
            last_run_timestamp="2024-01-01T12:00:00",
            last_status="success",
        )
        result = str(summary)
        assert "backup" in result
        assert "runs=5" in result
        assert "ok=4" in result
        assert "fail=1" in result
        assert "2.50s" in result

    def test_str_no_data(self):
        summary = JobSummary(
            job_name="noop",
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            avg_duration_seconds=None,
            last_run_timestamp=None,
            last_status=None,
        )
        result = str(summary)
        assert "never" in result
        assert "avg_duration=n/a" in result


class TestHistoryReporter:
    def test_summarize_job_counts(self, reporter, history):
        history.get_events.return_value = [
            make_event("success", 2.0),
            make_event("success", 4.0),
            make_event("failure", 1.0),
        ]
        summary = reporter.summarize_job("test_job")
        assert summary.total_runs == 3
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1

    def test_summarize_job_avg_duration(self, reporter, history):
        history.get_events.return_value = [
            make_event("success", 2.0),
            make_event("success", 4.0),
        ]
        summary = reporter.summarize_job("test_job")
        assert summary.avg_duration_seconds == pytest.approx(3.0)

    def test_summarize_job_no_events(self, reporter, history):
        history.get_events.return_value = []
        summary = reporter.summarize_job("test_job")
        assert summary.total_runs == 0
        assert summary.avg_duration_seconds is None
        assert summary.last_run_timestamp is None
        assert summary.last_status is None

    def test_summarize_job_last_event(self, reporter, history):
        history.get_events.return_value = [
            make_event("success", ts="2024-01-01T10:00:00"),
            make_event("failure", ts="2024-01-01T12:00:00"),
        ]
        summary = reporter.summarize_job("test_job")
        assert summary.last_status == "failure"
        assert summary.last_run_timestamp == "2024-01-01T12:00:00"

    def test_summarize_all(self, reporter, history):
        history.known_jobs.return_value = ["job_a", "job_b"]
        history.get_events.return_value = []
        summaries = reporter.summarize_all()
        assert len(summaries) == 2
        assert summaries[0].job_name == "job_a"
        assert summaries[1].job_name == "job_b"

    def test_avg_duration_skips_none(self, reporter, history):
        e1 = ExecutionEvent(job_name="test_job", executed_at="2024-01-01T00:00:00", status="success", duration_seconds=None)
        e2 = make_event("success", duration=6.0)
        history.get_events.return_value = [e1, e2]
        summary = reporter.summarize_job("test_job")
        assert summary.avg_duration_seconds == pytest.approx(6.0)
