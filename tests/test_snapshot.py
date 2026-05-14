"""Tests for snapshot, snapshot_builder, and snapshot_diff."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.snapshot import JobSnapshot, StatusSnapshot
from cronwatcher.snapshot_builder import SnapshotBuilder
from cronwatcher.snapshot_diff import SnapshotDiff, diff_snapshots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(jobs: dict) -> StatusSnapshot:
    snap = StatusSnapshot(captured_at="2024-01-01T00:00:00+00:00")
    for jid, kwargs in jobs.items():
        snap.jobs[jid] = JobSnapshot(job_id=jid, **kwargs)
    return snap


# ---------------------------------------------------------------------------
# JobSnapshot
# ---------------------------------------------------------------------------

class TestJobSnapshot:
    def test_to_dict_roundtrip(self):
        js = JobSnapshot(
            job_id="backup",
            last_seen="2024-01-01T12:00:00+00:00",
            is_overdue=False,
            silence_seconds=30.5,
            tags=["infra"],
        )
        assert JobSnapshot.from_dict(js.to_dict()) == js

    def test_missing_optional_fields_default(self):
        js = JobSnapshot.from_dict({"job_id": "x", "is_overdue": False})
        assert js.last_seen is None
        assert js.silence_seconds is None
        assert js.tags == []


# ---------------------------------------------------------------------------
# StatusSnapshot persistence
# ---------------------------------------------------------------------------

class TestStatusSnapshot:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "snap.json")
        snap = _make_snapshot(
            {"job_a": {"last_seen": None, "is_overdue": True, "silence_seconds": 120.0}}
        )
        snap.save(path)
        loaded = StatusSnapshot.load(path)
        assert loaded.jobs["job_a"].is_overdue is True
        assert loaded.captured_at == snap.captured_at

    def test_save_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "nested" / "dir" / "snap.json")
        snap = StatusSnapshot(captured_at="2024-01-01T00:00:00+00:00")
        snap.save(path)
        assert os.path.exists(path)


# ---------------------------------------------------------------------------
# SnapshotBuilder
# ---------------------------------------------------------------------------

@pytest.fixture
def builder_mocks():
    tracker = MagicMock()
    record = MagicMock()
    record.last_seen = datetime(2024, 1, 1, tzinfo=timezone.utc)
    tracker.jobs = {"nightly": record}
    tracker.is_overdue.return_value = False

    silence_detector = MagicMock()
    report = MagicMock()
    report.silence_duration_seconds.return_value = 45.0
    silence_detector.check.return_value = report

    tagger = MagicMock()
    tagger.tags_for_job.return_value = {"db", "nightly"}
    return tracker, silence_detector, tagger


class TestSnapshotBuilder:
    def test_build_creates_snapshot(self, builder_mocks):
        tracker, silence_detector, tagger = builder_mocks
        builder = SnapshotBuilder(tracker, silence_detector, tagger)
        snap = builder.build()
        assert "nightly" in snap.jobs
        js = snap.jobs["nightly"]
        assert js.is_overdue is False
        assert js.silence_seconds == 45.0
        assert set(js.tags) == {"db", "nightly"}

    def test_build_without_tagger(self, builder_mocks):
        tracker, silence_detector, _ = builder_mocks
        builder = SnapshotBuilder(tracker, silence_detector, tagger=None)
        snap = builder.build()
        assert snap.jobs["nightly"].tags == []


# ---------------------------------------------------------------------------
# diff_snapshots
# ---------------------------------------------------------------------------

class TestSnapshotDiff:
    def test_new_and_removed_jobs(self):
        prev = _make_snapshot({"a": {"last_seen": None, "is_overdue": False, "silence_seconds": None}})
        curr = _make_snapshot({"b": {"last_seen": None, "is_overdue": False, "silence_seconds": None}})
        diff = diff_snapshots(prev, curr)
        assert diff.new_jobs == ["b"]
        assert diff.removed_jobs == ["a"]

    def test_newly_overdue(self):
        prev = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": None}})
        curr = _make_snapshot({"x": {"last_seen": None, "is_overdue": True, "silence_seconds": None}})
        diff = diff_snapshots(prev, curr)
        assert "x" in diff.newly_overdue
        assert diff.recovered == []

    def test_recovered(self):
        prev = _make_snapshot({"x": {"last_seen": None, "is_overdue": True, "silence_seconds": None}})
        curr = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": None}})
        diff = diff_snapshots(prev, curr)
        assert "x" in diff.recovered

    def test_silence_increased(self):
        prev = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": 10.0}})
        curr = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": 70.0}})
        diff = diff_snapshots(prev, curr)
        assert diff.silence_increased["x"] == pytest.approx(60.0)

    def test_no_changes(self):
        prev = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": 5.0}})
        curr = _make_snapshot({"x": {"last_seen": None, "is_overdue": False, "silence_seconds": 5.0}})
        diff = diff_snapshots(prev, curr)
        assert not diff.has_changes
