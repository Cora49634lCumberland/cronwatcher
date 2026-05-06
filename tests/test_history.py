"""Tests for cronwatcher.history module."""

import json
import os
import time
import pytest

from cronwatcher.history import ExecutionEvent, JobHistory, HistoryStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    store_path = str(tmp_path / "history.json")
    return HistoryStore(path=store_path)


@pytest.fixture
def sample_event():
    return ExecutionEvent(
        job_name="backup",
        executed_at=1_700_000_000.0,
        expected_at=1_699_999_940.0,
        drift_seconds=60.0,
    )


# ---------------------------------------------------------------------------
# ExecutionEvent
# ---------------------------------------------------------------------------

class TestExecutionEvent:
    def test_to_dict_roundtrip(self, sample_event):
        d = sample_event.to_dict()
        restored = ExecutionEvent.from_dict(d)
        assert restored == sample_event

    def test_executed_dt_is_datetime(self, sample_event):
        from datetime import datetime
        assert isinstance(sample_event.executed_dt, datetime)

    def test_optional_fields_default_none(self):
        ev = ExecutionEvent(job_name="ping", executed_at=time.time())
        assert ev.expected_at is None
        assert ev.drift_seconds is None


# ---------------------------------------------------------------------------
# JobHistory
# ---------------------------------------------------------------------------

class TestJobHistory:
    def test_record_appends_event(self, sample_event):
        jh = JobHistory(job_name="backup")
        jh.record(sample_event)
        assert len(jh.events) == 1

    def test_max_events_enforced(self):
        jh = JobHistory(job_name="job", max_events=3)
        for i in range(5):
            jh.record(ExecutionEvent(job_name="job", executed_at=float(i)))
        assert len(jh.events) == 3
        assert jh.events[0].executed_at == 2.0  # oldest trimmed

    def test_last_n_returns_tail(self):
        jh = JobHistory(job_name="job")
        for i in range(10):
            jh.record(ExecutionEvent(job_name="job", executed_at=float(i)))
        last = jh.last_n(3)
        assert len(last) == 3
        assert last[-1].executed_at == 9.0

    def test_average_drift_no_events(self):
        jh = JobHistory(job_name="job")
        assert jh.average_drift() is None

    def test_average_drift_calculated(self):
        jh = JobHistory(job_name="job")
        for d in [10.0, 20.0, 30.0]:
            jh.record(ExecutionEvent(job_name="job", executed_at=0.0, drift_seconds=d))
        assert jh.average_drift() == 20.0


# ---------------------------------------------------------------------------
# HistoryStore
# ---------------------------------------------------------------------------

class TestHistoryStore:
    def test_get_creates_empty_history(self, tmp_store):
        jh = tmp_store.get("new_job")
        assert jh.job_name == "new_job"
        assert jh.events == []

    def test_record_event_persists(self, tmp_store, sample_event):
        tmp_store.record_event(sample_event)
        # Reload from disk
        reloaded = HistoryStore(path=tmp_store.path)
        jh = reloaded.get("backup")
        assert len(jh.events) == 1
        assert jh.events[0].drift_seconds == 60.0

    def test_all_jobs_lists_known_jobs(self, tmp_store, sample_event):
        tmp_store.record_event(sample_event)
        assert "backup" in tmp_store.all_jobs()

    def test_load_missing_file_is_empty(self, tmp_path):
        store = HistoryStore(path=str(tmp_path / "nonexistent.json"))
        assert store.all_jobs() == []
