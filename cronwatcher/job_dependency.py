"""Job dependency tracking: define upstream/downstream relationships between jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyViolation:
    job_name: str
    missing_upstream: List[str]

    def __repr__(self) -> str:
        deps = ", ".join(self.missing_upstream)
        return f"DependencyViolation(job={self.job_name!r}, missing=[{deps}])"


class DependencyGraph:
    """Tracks upstream dependencies between cron jobs."""

    def __init__(self) -> None:
        # job -> set of upstream jobs it depends on
        self._deps: Dict[str, Set[str]] = {}

    def add_dependency(self, job_name: str, depends_on: str) -> None:
        """Declare that *job_name* requires *depends_on* to have run first."""
        self._deps.setdefault(job_name, set()).add(depends_on)

    def remove_dependency(self, job_name: str, depends_on: str) -> None:
        if job_name in self._deps:
            self._deps[job_name].discard(depends_on)

    def upstream_jobs(self, job_name: str) -> List[str]:
        """Return the list of jobs that *job_name* depends on."""
        return sorted(self._deps.get(job_name, set()))

    def downstream_jobs(self, job_name: str) -> List[str]:
        """Return jobs that list *job_name* as an upstream dependency."""
        return sorted(
            name for name, deps in self._deps.items() if job_name in deps
        )

    def check_violations(
        self, job_name: str, completed_jobs: Set[str]
    ) -> Optional[DependencyViolation]:
        """Return a violation if any upstream deps of *job_name* are not completed."""
        upstream = self._deps.get(job_name, set())
        missing = sorted(upstream - completed_jobs)
        if missing:
            return DependencyViolation(job_name=job_name, missing_upstream=missing)
        return None

    def all_jobs(self) -> List[str]:
        """Return all jobs that have at least one registered dependency."""
        return sorted(self._deps.keys())
