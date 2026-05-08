"""CLI helper that prints a human-readable status table for all tracked jobs."""

from datetime import datetime
from typing import Optional

from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.recovery_detector import RecoveryDetector


_COL_WIDTH = 20


def _fmt(value: Optional[datetime]) -> str:
    if value is None:
        return "never"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _status_label(tracker: HeartbeatTracker, job_name: str, interval: float) -> str:
    record = tracker.get(job_name)
    if record is None or record.last_seen is None:
        return "UNKNOWN"
    if tracker.is_overdue(job_name, interval):
        return "OVERDUE"
    return "OK"


def build_status_table(
    tracker: HeartbeatTracker,
    intervals: dict[str, float],
    recovery_detector: Optional[RecoveryDetector] = None,
) -> str:
    """Return a formatted status table string for all jobs in *intervals*."""
    header = (
        f"{'JOB':<{_COL_WIDTH}} "
        f"{'STATUS':<10} "
        f"{'LAST SEEN':<22} "
        f"{'INTERVAL(s)':<12}"
    )
    separator = "-" * len(header)
    rows = [header, separator]

    recovering = set()
    if recovery_detector is not None:
        recovering = set(recovery_detector.overdue_jobs)

    for job_name, interval in sorted(intervals.items()):
        status = _status_label(tracker, job_name, interval)
        if job_name in recovering:
            status = "RECOVERING"
        record = tracker.get(job_name)
        last_seen_str = _fmt(record.last_seen if record else None)
        rows.append(
            f"{job_name:<{_COL_WIDTH}} "
            f"{status:<10} "
            f"{last_seen_str:<22} "
            f"{interval:<12.1f}"
        )

    rows.append(separator)
    rows.append(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return "\n".join(rows)


def print_status(
    tracker: HeartbeatTracker,
    intervals: dict[str, float],
    recovery_detector: Optional[RecoveryDetector] = None,
) -> None:  # pragma: no cover
    """Print the status table to stdout."""
    print(build_status_table(tracker, intervals, recovery_detector))
