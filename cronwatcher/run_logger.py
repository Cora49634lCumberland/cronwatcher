"""run_logger.py — Records structured run outcomes (success/failure) for cron jobs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class RunOutcome:
    job_name: str
    status: str  # "success" | "failure"
    timestamp: str  # ISO-8601
    exit_code: Optional[int] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "status": self.status,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RunOutcome":
        return cls(
            job_name=data["job_name"],
            status=data["status"],
            timestamp=data["timestamp"],
            exit_code=data.get("exit_code"),
            message=data.get("message"),
        )

    @property
    def executed_dt(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)

    def __repr__(self) -> str:
        return (
            f"RunOutcome(job={self.job_name!r}, status={self.status!r}, "
            f"ts={self.timestamp!r})"
        )


class RunLogger:
    """Persists RunOutcome records to a newline-delimited JSON file."""

    def __init__(self, store_path: str) -> None:
        self.store_path = store_path

    def record(self, outcome: RunOutcome) -> None:
        """Append a run outcome to the store."""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True) if os.path.dirname(self.store_path) else None
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(outcome.to_dict()) + "\n")

    def load(self, job_name: Optional[str] = None) -> List[RunOutcome]:
        """Load all outcomes, optionally filtered by job_name."""
        if not os.path.exists(self.store_path):
            return []
        outcomes: List[RunOutcome] = []
        with open(self.store_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    outcome = RunOutcome.from_dict(data)
                    if job_name is None or outcome.job_name == job_name:
                        outcomes.append(outcome)
                except (json.JSONDecodeError, KeyError):
                    continue
        return outcomes

    def latest(self, job_name: str) -> Optional[RunOutcome]:
        """Return the most recent outcome for a given job, or None."""
        records = self.load(job_name=job_name)
        if not records:
            return None
        return max(records, key=lambda r: r.timestamp)

    @staticmethod
    def make_outcome(
        job_name: str,
        status: str,
        exit_code: Optional[int] = None,
        message: Optional[str] = None,
    ) -> RunOutcome:
        """Factory that stamps the current UTC time."""
        return RunOutcome(
            job_name=job_name,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            exit_code=exit_code,
            message=message,
        )
