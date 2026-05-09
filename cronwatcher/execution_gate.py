"""Execution gate: prevent overlapping cron job runs and track lock state."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LockEntry:
    job_name: str
    pid: int
    acquired_at: float = field(default_factory=time.time)
    timeout_seconds: float = 300.0

    def is_expired(self, now: Optional[float] = None) -> bool:
        """Return True if the lock has exceeded its timeout."""
        now = now if now is not None else time.time()
        return (now - self.acquired_at) >= self.timeout_seconds

    def held_for_seconds(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        return now - self.acquired_at

    def __repr__(self) -> str:
        return (
            f"LockEntry(job={self.job_name!r}, pid={self.pid}, "
            f"held={self.held_for_seconds():.1f}s, "
            f"timeout={self.timeout_seconds}s)"
        )


class ExecutionGate:
    """In-memory lock manager that prevents concurrent job execution."""

    def __init__(self) -> None:
        self._locks: Dict[str, LockEntry] = {}

    def acquire(self, job_name: str, pid: int, timeout_seconds: float = 300.0) -> bool:
        """Try to acquire a lock for *job_name*.

        Returns True if the lock was granted, False if already held by a
        non-expired lock.
        """
        existing = self._locks.get(job_name)
        if existing is not None and not existing.is_expired():
            return False
        self._locks[job_name] = LockEntry(
            job_name=job_name, pid=pid, timeout_seconds=timeout_seconds
        )
        return True

    def release(self, job_name: str, pid: int) -> bool:
        """Release the lock for *job_name* if held by *pid*.

        Returns True if the lock was released, False otherwise.
        """
        entry = self._locks.get(job_name)
        if entry is None or entry.pid != pid:
            return False
        del self._locks[job_name]
        return True

    def is_locked(self, job_name: str) -> bool:
        """Return True if *job_name* has an active (non-expired) lock."""
        entry = self._locks.get(job_name)
        return entry is not None and not entry.is_expired()

    def get_lock(self, job_name: str) -> Optional[LockEntry]:
        return self._locks.get(job_name)

    def expire_stale_locks(self) -> list[str]:
        """Remove expired locks and return names of jobs whose locks were cleared."""
        stale = [name for name, entry in self._locks.items() if entry.is_expired()]
        for name in stale:
            del self._locks[name]
        return stale

    def active_jobs(self) -> list[str]:
        """Return names of jobs with active (non-expired) locks."""
        return [name for name, entry in self._locks.items() if not entry.is_expired()]
