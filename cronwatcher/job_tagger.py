"""High-level facade that integrates TagIndex with JobRegistry.

JobTagger wraps an existing JobRegistry and a TagIndex so callers can
query jobs by tag without touching the registry internals.
"""
from __future__ import annotations

from typing import Iterable, List, Set

from cronwatcher.job_registry import JobRegistry
from cronwatcher.tag_filter import TagFilter, TagIndex


class JobTagger:
    """Attach and query tags on registered jobs."""

    def __init__(self, registry: JobRegistry) -> None:
        self._registry = registry
        self._index = TagIndex()
        self._filter = TagFilter(self._index)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def tag_job(self, job_name: str, tags: Iterable[str]) -> None:
        """Add *tags* to an existing job.  Raises KeyError if unknown."""
        _ = self._registry.get(job_name)  # validate existence
        self._index.add(job_name, tags)

    def untag_job(self, job_name: str) -> None:
        """Remove all tags from *job_name*."""
        self._index.remove(job_name)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def tags_for_job(self, job_name: str) -> Set[str]:
        """Return the set of tags assigned to *job_name*."""
        return self._index.tags_for_job(job_name)

    def jobs_with_any(self, *tags: str) -> List[str]:
        """Return job names carrying at least one of the given tags."""
        all_names = self._registry.all_names()
        return self._filter.match_any(all_names, tags)

    def jobs_with_all(self, *tags: str) -> List[str]:
        """Return job names carrying all of the given tags."""
        all_names = self._registry.all_names()
        return self._filter.match_all(all_names, list(tags))

    def jobs_excluding(self, *tags: str) -> List[str]:
        """Return job names carrying none of the given tags."""
        all_names = self._registry.all_names()
        return self._filter.exclude(all_names, tags)

    def all_tags(self) -> List[str]:
        """Return a sorted list of every tag that is currently in use."""
        return self._index.all_tags()

    def jobs_without_tags(self) -> List[str]:
        """Return job names that have no tags assigned.

        Useful for auditing a registry to find jobs that have not yet
        been categorised.
        """
        return [
            name
            for name in self._registry.all_names()
            if not self._index.tags_for_job(name)
        ]
