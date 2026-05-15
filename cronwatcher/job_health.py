"""Aggregate health scoring for monitored cron jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.drift import DriftAnalyzer
from cronwatcher.silence_detector import SilenceDetector
from cronwatcher.recovery_detector import RecoveryDetector


@dataclass
class HealthScore:
    """Computed health score for a single job."""

    job_name: str
    score: float  # 0.0 (critical) to 1.0 (healthy)
    is_overdue: bool
    is_silent: bool
    drift_seconds: Optional[float]
    recently_recovered: bool
    label: str = field(init=False)

    def __post_init__(self) -> None:
        if self.score >= 0.8:
            self.label = "healthy"
        elif self.score >= 0.5:
            self.label = "degraded"
        else:
            self.label = "critical"

    def __repr__(self) -> str:
        return (
            f"HealthScore(job={self.job_name!r}, score={self.score:.2f},"
            f" label={self.label!r})"
        )


class JobHealthScorer:
    """Computes a composite health score for each registered job."""

    def __init__(
        self,
        heartbeat: HeartbeatTracker,
        drift_analyzer: DriftAnalyzer,
        silence_detector: SilenceDetector,
        recovery_detector: RecoveryDetector,
        drift_penalty_per_second: float = 0.01,
        max_drift_penalty: float = 0.4,
    ) -> None:
        self._heartbeat = heartbeat
        self._drift = drift_analyzer
        self._silence = silence_detector
        self._recovery = recovery_detector
        self._drift_penalty_per_second = drift_penalty_per_second
        self._max_drift_penalty = max_drift_penalty

    def score_job(self, job_name: str, interval_seconds: float) -> HealthScore:
        """Return a HealthScore for *job_name*."""
        overdue = self._heartbeat.is_overdue(job_name, interval_seconds)
        silence_report = self._silence.check(job_name, interval_seconds)
        silent = silence_report is not None

        drift_record = self._drift.latest(job_name)
        drift_secs: Optional[float] = None
        drift_penalty = 0.0
        if drift_record is not None:
            drift_secs = abs(drift_record.drift_seconds())
            drift_penalty = min(
                drift_secs * self._drift_penalty_per_second,
                self._max_drift_penalty,
            )

        recovery_event = self._recovery.check_job(job_name, interval_seconds)
        recovered = recovery_event is not None

        score = 1.0
        if overdue:
            score -= 0.5
        if silent:
            score -= 0.3
        score -= drift_penalty
        if recovered:
            score = min(score + 0.1, 1.0)
        score = max(0.0, min(1.0, score))

        return HealthScore(
            job_name=job_name,
            score=score,
            is_overdue=overdue,
            is_silent=silent,
            drift_seconds=drift_secs,
            recently_recovered=recovered,
        )

    def score_all(self, job_intervals: dict[str, float]) -> list[HealthScore]:
        """Score every job in *job_intervals* mapping {name: interval_seconds}."""
        return [self.score_job(name, secs) for name, secs in job_intervals.items()]
