"""Snapshot: capture and persist a point-in-time status of all monitored jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class JobSnapshot:
    job_id: str
    last_seen: Optional[str]          # ISO-8601 or None
    is_overdue: bool
    silence_seconds: Optional[float]
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "last_seen": self.last_seen,
            "is_overdue": self.is_overdue,
            "silence_seconds": self.silence_seconds,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobSnapshot":
        return cls(
            job_id=data["job_id"],
            last_seen=data.get("last_seen"),
            is_overdue=data["is_overdue"],
            silence_seconds=data.get("silence_seconds"),
            tags=data.get("tags", []),
        )


@dataclass
class StatusSnapshot:
    captured_at: str
    jobs: Dict[str, JobSnapshot] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at,
            "jobs": {jid: js.to_dict() for jid, js in self.jobs.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatusSnapshot":
        snap = cls(captured_at=data["captured_at"])
        for jid, jdata in data.get("jobs", {}).items():
            snap.jobs[jid] = JobSnapshot.from_dict(jdata)
        return snap

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> "StatusSnapshot":
        with open(path) as fh:
            return cls.from_dict(json.load(fh))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
