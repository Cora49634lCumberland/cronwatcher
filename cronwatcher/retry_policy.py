"""Retry policy configuration and evaluation for cron jobs."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class RetryPolicy:
    """Defines how a job should be retried on failure."""

    max_attempts: int = 3
    backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 3600.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be non-negative")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the delay in seconds before the given attempt (1-indexed)."""
        if attempt <= 1:
            return 0.0
        delay = self.backoff_seconds * (self.backoff_multiplier ** (attempt - 2))
        return min(delay, self.max_backoff_seconds)

    def next_retry_at(self, last_attempt_at: datetime, attempt: int) -> Optional[datetime]:
        """Return when the next retry should occur, or None if exhausted."""
        if attempt >= self.max_attempts:
            return None
        delay = self.delay_for_attempt(attempt + 1)
        return last_attempt_at + timedelta(seconds=delay)

    def is_exhausted(self, attempt: int) -> bool:
        """Return True if no more retries are allowed."""
        return attempt >= self.max_attempts


@dataclass
class RetryState:
    """Tracks the current retry state for a specific job."""

    job_name: str
    attempt: int = 0
    last_attempt_at: Optional[datetime] = None
    succeeded: bool = False

    def record_attempt(self, at: Optional[datetime] = None) -> None:
        self.attempt += 1
        self.last_attempt_at = at or datetime.utcnow()

    def record_success(self) -> None:
        self.succeeded = True

    def reset(self) -> None:
        self.attempt = 0
        self.last_attempt_at = None
        self.succeeded = False

    def __repr__(self) -> str:
        return (
            f"RetryState(job={self.job_name!r}, attempt={self.attempt}, "
            f"succeeded={self.succeeded})"
        )
