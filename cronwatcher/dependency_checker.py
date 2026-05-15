from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.job_dependency import DependencyGraph, DependencyViolation
from cronwatcher.heartbeat import HeartbeatTracker


@dataclass
class CheckResult:
    job_name: str
    violations: List[DependencyViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def __repr__(self) -> str:
        if self.passed:
            return f"CheckResult({self.job_name!r}: OK)"
        names = ", ".join(v.upstream for v in self.violations)
        return f"CheckResult({self.job_name!r}: BLOCKED by [{names}])"


class DependencyChecker:
    """Checks whether upstream dependencies have completed before a job runs."""

    def __init__(
        self,
        graph: DependencyGraph,
        tracker: HeartbeatTracker,
        max_staleness_seconds: float = 3600.0,
    ) -> None:
        self._graph = graph
        self._tracker = tracker
        self._max_staleness = max_staleness_seconds

    def _completed_jobs(self) -> set:
        """Return job names that have a recent heartbeat within staleness window."""
        completed = set()
        for name, record in self._tracker.all_records().items():
            if record.last_seen is not None:
                import time
                age = time.time() - record.last_seen
                if age <= self._max_staleness:
                    completed.add(name)
        return completed

    def check(self, job_name: str) -> CheckResult:
        """Check whether all upstream dependencies of *job_name* have completed."""
        upstreams = self._graph.upstream_jobs(job_name)
        completed = self._completed_jobs()
        violations = [
            DependencyViolation(upstream=up, downstream=job_name)
            for up in upstreams
            if up not in completed
        ]
        return CheckResult(job_name=job_name, violations=violations)

    def check_all(self, job_names: List[str]) -> List[CheckResult]:
        """Run dependency checks for every job in *job_names*."""
        return [self.check(name) for name in job_names]
