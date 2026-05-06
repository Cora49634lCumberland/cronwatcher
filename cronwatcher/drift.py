"""Drift detection: measures execution time deviation from expected schedule."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class DriftRecord:
    job_name: str
    expected_at: datetime
    actual_at: datetime

    @property
    def drift_seconds(self) -> float:
        """Positive means late, negative means early."""
        return (self.actual_at - self.expected_at).total_seconds()

    @property
    def is_late(self) -> bool:
        return self.drift_seconds > 0

    def __repr__(self) -> str:
        direction = "late" if self.is_late else "early"
        return (
            f"DriftRecord(job={self.job_name!r}, "
            f"drift={abs(self.drift_seconds):.1f}s {direction})"
        )


@dataclass
class DriftAnalyzer:
    threshold_seconds: float = 60.0
    history: Dict[str, List[DriftRecord]] = field(default_factory=dict)

    def record(self, job_name: str, expected_at: datetime, actual_at: datetime) -> DriftRecord:
        record = DriftRecord(job_name=job_name, expected_at=expected_at, actual_at=actual_at)
        self.history.setdefault(job_name, []).append(record)
        return record

    def is_drifting(self, job_name: str) -> bool:
        records = self.history.get(job_name, [])
        if not records:
            return False
        latest = records[-1]
        return abs(latest.drift_seconds) > self.threshold_seconds

    def average_drift(self, job_name: str) -> Optional[float]:
        records = self.history.get(job_name, [])
        if not records:
            return None
        return sum(r.drift_seconds for r in records) / len(records)

    def clear_history(self, job_name: str) -> None:
        self.history.pop(job_name, None)
