"""Tag-based filtering for job registries.

Allows jobs to be labelled with tags and queried/filtered by those tags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set


@dataclass
class TagIndex:
    """Maintains a mapping from tag names to sets of job names."""

    _index: Dict[str, Set[str]] = field(default_factory=dict, init=False, repr=False)

    def add(self, job_name: str, tags: Iterable[str]) -> None:
        """Register *tags* for *job_name*."""
        for tag in tags:
            self._index.setdefault(tag, set()).add(job_name)

    def remove(self, job_name: str) -> None:
        """Remove all tag associations for *job_name*."""
        for members in self._index.values():
            members.discard(job_name)

    def jobs_for_tag(self, tag: str) -> Set[str]:
        """Return the set of job names that carry *tag*."""
        return set(self._index.get(tag, set()))

    def tags_for_job(self, job_name: str) -> Set[str]:
        """Return the set of tags assigned to *job_name*."""
        return {tag for tag, members in self._index.items() if job_name in members}

    def all_tags(self) -> List[str]:
        """Return a sorted list of every known tag."""
        return sorted(self._index.keys())


class TagFilter:
    """Filter a collection of job names by tag expressions."""

    def __init__(self, index: TagIndex) -> None:
        self._index = index

    def match_any(self, job_names: Iterable[str], tags: Iterable[str]) -> List[str]:
        """Return jobs from *job_names* that carry **at least one** of *tags*."""
        wanted: Set[str] = set()
        for tag in tags:
            wanted |= self._index.jobs_for_tag(tag)
        return [j for j in job_names if j in wanted]

    def match_all(self, job_names: Iterable[str], tags: Iterable[str]) -> List[str]:
        """Return jobs from *job_names* that carry **all** of *tags*."""
        tag_list = list(tags)
        if not tag_list:
            return list(job_names)
        required: Optional[Set[str]] = None
        for tag in tag_list:
            candidates = self._index.jobs_for_tag(tag)
            required = candidates if required is None else required & candidates
        required = required or set()
        return [j for j in job_names if j in required]

    def exclude(self, job_names: Iterable[str], tags: Iterable[str]) -> List[str]:
        """Return jobs from *job_names* that carry **none** of *tags*."""
        excluded: Set[str] = set()
        for tag in tags:
            excluded |= self._index.jobs_for_tag(tag)
        return [j for j in job_names if j not in excluded]
