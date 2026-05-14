"""CLI helper: print a status table filtered by job tags."""
from __future__ import annotations

from typing import List, Optional

from cronwatcher.cli_status import build_status_table, print_status
from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.job_registry import JobRegistry
from cronwatcher.job_tagger import JobTagger


def print_tagged_status(
    registry: JobRegistry,
    tracker: HeartbeatTracker,
    tagger: JobTagger,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
) -> None:
    """Print a status table limited to jobs matching the tag criteria.

    Parameters
    ----------
    registry:
        The full job registry.
    tracker:
        Heartbeat tracker used to determine overdue status.
    tagger:
        JobTagger instance holding tag assignments.
    include_tags:
        If given, only jobs carrying **at least one** of these tags are shown.
    exclude_tags:
        If given, jobs carrying **any** of these tags are hidden.
    """
    all_names: List[str] = registry.all_names()

    if include_tags:
        all_names = tagger.jobs_with_any(*include_tags)

    if exclude_tags:
        all_names = tagger.jobs_excluding(*exclude_tags) if not include_tags else [
            j for j in all_names if j not in tagger.jobs_with_any(*exclude_tags)
        ]

    if not all_names:
        print("No jobs match the given tag filters.")
        return

    filtered_registry = _subset_registry(registry, all_names)
    rows = build_status_table(filtered_registry, tracker)
    print_status(rows)


def _subset_registry(registry: JobRegistry, names: List[str]) -> JobRegistry:
    """Return a new JobRegistry containing only the named jobs."""
    sub = JobRegistry()
    for name in names:
        cfg = registry.get(name)
        sub.register(
            name,
            expression=cfg.expression,
            timeout_seconds=cfg.timeout_seconds,
        )
    return sub
