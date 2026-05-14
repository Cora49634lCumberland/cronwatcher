"""Build a StatusSnapshot from live daemon state."""
from __future__ import annotations

from typing import Optional

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.job_tagger import JobTagger
from cronwatcher.silence_detector import SilenceDetector
from cronwatcher.snapshot import JobSnapshot, StatusSnapshot, now_iso


class SnapshotBuilder:
    """Assembles a StatusSnapshot from injected components."""

    def __init__(
        self,
        tracker: HeartbeatTracker,
        silence_detector: SilenceDetector,
        tagger: Optional[JobTagger] = None,
    ) -> None:
        self._tracker = tracker
        self._silence = silence_detector
        self._tagger = tagger

    def build(self) -> StatusSnapshot:
        snap = StatusSnapshot(captured_at=now_iso())
        for job_id, record in self._tracker.jobs.items():
            last_seen = (
                record.last_seen.isoformat() if record.last_seen is not None else None
            )
            overdue = self._tracker.is_overdue(job_id)
            report = self._silence.check(job_id)
            silence_secs = report.silence_duration_seconds() if report else None
            tags = (
                list(self._tagger.tags_for_job(job_id)) if self._tagger else []
            )
            snap.jobs[job_id] = JobSnapshot(
                job_id=job_id,
                last_seen=last_seen,
                is_overdue=overdue,
                silence_seconds=silence_secs,
                tags=tags,
            )
        return snap
