"""Tests for cronwatcher.run_logger."""

import os
from datetime import datetime, timezone

import pytest

from cronwatcher.run_logger import RunLogger, RunOutcome


@pytest.fixture
def tmp_store(tmp_path):
    return str(tmp_path / "runs.jsonl")


@pytest.fixture
def logger(tmp_store):
    return RunLogger(store_path=tmp_store)


@pytest.fixture
def sample_outcome():
    return RunOutcome(
        job_name="backup",
        status="success",
        timestamp="2024-06-01T12:00:00+00:00",
        exit_code=0,
        message="completed ok",
    )


class TestRunOutcome:
    def test_to_dict_roundtrip(self, sample_outcome):
        d = sample_outcome.to_dict()
        restored = RunOutcome.from_dict(d)
        assert restored.job_name == sample_outcome.job_name
        assert restored.status == sample_outcome.status
        assert restored.exit_code == sample_outcome.exit_code
        assert restored.message == sample_outcome.message

    def test_executed_dt_is_datetime(self, sample_outcome):
        dt = sample_outcome.executed_dt
        assert isinstance(dt, datetime)
        assert dt.year == 2024

    def test_repr_contains_job_name(self, sample_outcome):
        assert "backup" in repr(sample_outcome)

    def test_from_dict_missing_optional_fields(self):
        data = {"job_name": "sync", "status": "failure", "timestamp": "2024-01-01T00:00:00+00:00"}
        outcome = RunOutcome.from_dict(data)
        assert outcome.exit_code is None
        assert outcome.message is None


class TestRunLogger:
    def test_record_and_load(self, logger, sample_outcome):
        logger.record(sample_outcome)
        results = logger.load()
        assert len(results) == 1
        assert results[0].job_name == "backup"

    def test_load_empty_when_no_file(self, logger):
        results = logger.load()
        assert results == []

    def test_load_filtered_by_job_name(self, logger):
        logger.record(RunOutcome("job_a", "success", "2024-01-01T00:00:00+00:00"))
        logger.record(RunOutcome("job_b", "failure", "2024-01-02T00:00:00+00:00"))
        results = logger.load(job_name="job_a")
        assert len(results) == 1
        assert results[0].job_name == "job_a"

    def test_latest_returns_most_recent(self, logger):
        logger.record(RunOutcome("deploy", "success", "2024-03-01T10:00:00+00:00"))
        logger.record(RunOutcome("deploy", "failure", "2024-03-02T10:00:00+00:00"))
        latest = logger.latest("deploy")
        assert latest is not None
        assert latest.status == "failure"

    def test_latest_returns_none_for_unknown_job(self, logger):
        assert logger.latest("unknown") is None

    def test_make_outcome_stamps_utc_time(self):
        outcome = RunLogger.make_outcome("nightly", "success", exit_code=0)
        dt = outcome.executed_dt
        assert isinstance(dt, datetime)
        assert outcome.job_name == "nightly"
        assert outcome.status == "success"

    def test_multiple_records_appended(self, logger):
        for i in range(5):
            logger.record(RunOutcome("job", "success", f"2024-01-0{i+1}T00:00:00+00:00"))
        assert len(logger.load()) == 5
