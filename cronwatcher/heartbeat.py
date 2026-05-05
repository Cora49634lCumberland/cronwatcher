"""Heartbeat tracker for cron job execution times.

Records timestamps of cron job executions and detects drift or silence
based on configured expected intervals.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    """Stores execution metadata for a single cron job."""
    name: str
    expected_interval_seconds: float
    last_seen: Optional[float] = None
    missed_count: int = 0
    drift_threshold_seconds: float = 60.0

    def record_execution(self) -> None:
        """Update last_seen to the current timestamp."""
        now = time.time()
        if self.last_seen is not None:
            actual_interval = now - self.last_seen
            drift = abs(actual_interval - self.expected_interval_seconds)
            if drift > self.drift_threshold_seconds:
                logger.warning(
                    "Drift detected for job '%s': expected %.1fs interval, "
                    "got %.1fs (drift=%.1fs)",
                    self.name,
                    self.expected_interval_seconds,
                    actual_interval,
                    drift,
                )
        self.last_seen = now
        self.missed_count = 0
        logger.debug("Heartbeat recorded for job '%s' at %.3f", self.name, now)

    def is_overdue(self, grace_period_seconds: float = 0.0) -> bool:
        """Return True if the job has not run within its expected interval."""
        if self.last_seen is None:
            return False
        elapsed = time.time() - self.last_seen
        return elapsed > (self.expected_interval_seconds + grace_period_seconds)


class HeartbeatTracker:
    """Manages heartbeat records for multiple cron jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}

    def register(self, name: str, expected_interval_seconds: float,
                 drift_threshold_seconds: float = 60.0) -> None:
        """Register a new cron job to monitor."""
        if name in self._jobs:
            raise ValueError(f"Job '{name}' is already registered.")
        self._jobs[name] = JobRecord(
            name=name,
            expected_interval_seconds=expected_interval_seconds,
            drift_threshold_seconds=drift_threshold_seconds,
        )
        logger.info("Registered job '%s' with interval %.1fs", name, expected_interval_seconds)

    def ping(self, name: str) -> None:
        """Record a heartbeat for the given job name."""
        if name not in self._jobs:
            raise KeyError(f"Unknown job '{name}'. Register it first.")
        self._jobs[name].record_execution()

    def check_all(self, grace_period_seconds: float = 30.0) -> Dict[str, bool]:
        """Return a mapping of job name -> overdue status."""
        results = {}
        for name, record in self._jobs.items():
            overdue = record.is_overdue(grace_period_seconds)
            if overdue:
                record.missed_count += 1
                logger.warning(
                    "Job '%s' is overdue (missed_count=%d).",
                    name,
                    record.missed_count,
                )
            results[name] = overdue
        return results

    def unregister(self, name: str) -> None:
        """Remove a previously registered job from monitoring.

        Raises:
            KeyError: If the job name is not currently registered.
        """
        if name not in self._jobs:
            raise KeyError(f"Unknown job '{name}'. Cannot unregister.")
        del self._jobs[name]
        logger.info("Unregistered job '%s'", name)

    def status(self, name: str) -> JobRecord:
        """Return the JobRecord for the given job name.

        Raises:
            KeyError: If the job name is not currently registered.
        """
        if name not in self._jobs:
            raise KeyError(f"Unknown job '{name}'. Register it first.")
        return self._jobs[name]
