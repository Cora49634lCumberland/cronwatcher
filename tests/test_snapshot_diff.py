"""Focused edge-case tests for snapshot_diff."""
from __future__ import annotations

from cronwatcher.snapshot import JobSnapshot, StatusSnapshot
from cronwatcher.snapshot_diff import diff_snapshots


def _snap(*job_tuples) -> StatusSnapshot:
    """Build a StatusSnapshot from (job_id, is_overdue, silence_seconds) tuples."""
    s = StatusSnapshot(captured_at="2024-06-01T00:00:00+00:00")
    for job_id, is_overdue, silence_seconds in job_tuples:
        s.jobs[job_id] = JobSnapshot(
            job_id=job_id,
            last_seen=None,
            is_overdue=is_overdue,
            silence_seconds=silence_seconds,
        )
    return s


def test_empty_snapshots_no_diff():
    diff = diff_snapshots(StatusSnapshot(captured_at="t"), StatusSnapshot(captured_at="t"))
    assert not diff.has_changes


def test_silence_not_flagged_when_decreased():
    prev = _snap(("j", False, 100.0))
    curr = _snap(("j", False, 50.0))
    diff = diff_snapshots(prev, curr)
    assert "j" not in diff.silence_increased
    assert not diff.has_changes


def test_silence_none_to_value_flagged():
    prev = _snap(("j", False, None))
    curr = _snap(("j", False, 20.0))
    diff = diff_snapshots(prev, curr)
    assert diff.silence_increased["j"] == 20.0


def test_multiple_jobs_independent():
    prev = _snap(("a", False, 0.0), ("b", True, 0.0))
    curr = _snap(("a", True, 0.0), ("b", False, 0.0))
    diff = diff_snapshots(prev, curr)
    assert "a" in diff.newly_overdue
    assert "b" in diff.recovered
    assert diff.new_jobs == []
    assert diff.removed_jobs == []


def test_repr_contains_key_fields():
    prev = _snap(("x", False, None))
    curr = _snap(("x", True, None))
    diff = diff_snapshots(prev, curr)
    r = repr(diff)
    assert "newly_overdue" in r
    assert "x" in r
