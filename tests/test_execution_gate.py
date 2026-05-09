"""Tests for cronwatcher.execution_gate."""

import time
import pytest
from cronwatcher.execution_gate import ExecutionGate, LockEntry


@pytest.fixture
def gate() -> ExecutionGate:
    return ExecutionGate()


class TestLockEntry:
    def test_not_expired_immediately(self):
        entry = LockEntry(job_name="job", pid=1, timeout_seconds=60)
        assert not entry.is_expired()

    def test_expired_when_past_timeout(self):
        entry = LockEntry(job_name="job", pid=1, acquired_at=time.time() - 400, timeout_seconds=300)
        assert entry.is_expired()

    def test_held_for_seconds_approximate(self):
        entry = LockEntry(job_name="job", pid=42, acquired_at=time.time() - 10)
        assert 9 <= entry.held_for_seconds() <= 12

    def test_repr_contains_job_name(self):
        entry = LockEntry(job_name="myjob", pid=99)
        assert "myjob" in repr(entry)
        assert "99" in repr(entry)


class TestExecutionGate:
    def test_acquire_succeeds_for_new_job(self, gate):
        assert gate.acquire("backup", pid=100) is True

    def test_acquire_fails_when_locked(self, gate):
        gate.acquire("backup", pid=100)
        assert gate.acquire("backup", pid=200) is False

    def test_acquire_different_jobs_independent(self, gate):
        assert gate.acquire("job_a", pid=1) is True
        assert gate.acquire("job_b", pid=2) is True

    def test_release_by_owner_succeeds(self, gate):
        gate.acquire("backup", pid=100)
        assert gate.release("backup", pid=100) is True
        assert not gate.is_locked("backup")

    def test_release_by_non_owner_fails(self, gate):
        gate.acquire("backup", pid=100)
        assert gate.release("backup", pid=999) is False
        assert gate.is_locked("backup")

    def test_release_unknown_job_returns_false(self, gate):
        assert gate.release("unknown", pid=1) is False

    def test_is_locked_false_when_not_acquired(self, gate):
        assert not gate.is_locked("nojob")

    def test_is_locked_true_after_acquire(self, gate):
        gate.acquire("sync", pid=5)
        assert gate.is_locked("sync")

    def test_expired_lock_allows_reacquire(self, gate):
        # Manually insert an expired lock
        gate._locks["old_job"] = LockEntry(
            job_name="old_job", pid=77, acquired_at=time.time() - 400, timeout_seconds=300
        )
        assert gate.acquire("old_job", pid=88) is True

    def test_expire_stale_locks_removes_expired(self, gate):
        gate._locks["stale"] = LockEntry(
            job_name="stale", pid=1, acquired_at=time.time() - 400, timeout_seconds=300
        )
        gate.acquire("fresh", pid=2, timeout_seconds=300)
        removed = gate.expire_stale_locks()
        assert "stale" in removed
        assert "fresh" not in removed
        assert gate.is_locked("fresh")

    def test_active_jobs_excludes_expired(self, gate):
        gate.acquire("active", pid=10)
        gate._locks["dead"] = LockEntry(
            job_name="dead", pid=20, acquired_at=time.time() - 400, timeout_seconds=300
        )
        active = gate.active_jobs()
        assert "active" in active
        assert "dead" not in active

    def test_get_lock_returns_entry(self, gate):
        gate.acquire("myjob", pid=55)
        entry = gate.get_lock("myjob")
        assert entry is not None
        assert entry.pid == 55

    def test_get_lock_returns_none_for_unknown(self, gate):
        assert gate.get_lock("ghost") is None
