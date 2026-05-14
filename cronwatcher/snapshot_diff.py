"""Diff two StatusSnapshots to surface changes between captures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronwatcher.snapshot import StatusSnapshot


@dataclass
class SnapshotDiff:
    new_jobs: List[str] = field(default_factory=list)
    removed_jobs: List[str] = field(default_factory=list)
    newly_overdue: List[str] = field(default_factory=list)
    recovered: List[str] = field(default_factory=list)
    silence_increased: Dict[str, float] = field(default_factory=dict)  # job_id -> delta

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_jobs
            or self.removed_jobs
            or self.newly_overdue
            or self.recovered
            or self.silence_increased
        )

    def __repr__(self) -> str:
        return (
            f"SnapshotDiff(new={self.new_jobs}, removed={self.removed_jobs}, "
            f"newly_overdue={self.newly_overdue}, recovered={self.recovered}, "
            f"silence_increased={self.silence_increased})"
        )


def diff_snapshots(previous: StatusSnapshot, current: StatusSnapshot) -> SnapshotDiff:
    """Compare two snapshots and return a SnapshotDiff describing what changed."""
    prev_ids = set(previous.jobs)
    curr_ids = set(current.jobs)

    result = SnapshotDiff()
    result.new_jobs = sorted(curr_ids - prev_ids)
    result.removed_jobs = sorted(prev_ids - curr_ids)

    for job_id in curr_ids & prev_ids:
        prev_job = previous.jobs[job_id]
        curr_job = current.jobs[job_id]

        if curr_job.is_overdue and not prev_job.is_overdue:
            result.newly_overdue.append(job_id)
        elif not curr_job.is_overdue and prev_job.is_overdue:
            result.recovered.append(job_id)

        prev_sil = prev_job.silence_seconds or 0.0
        curr_sil = curr_job.silence_seconds or 0.0
        if curr_sil > prev_sil:
            result.silence_increased[job_id] = round(curr_sil - prev_sil, 3)

    return result
