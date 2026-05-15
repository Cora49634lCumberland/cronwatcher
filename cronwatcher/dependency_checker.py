"""DependencyChecker: integrates DependencyGraph with HeartbeatTracker to
validate that upstream jobs have run before a downstream job is allowed."""
from __future__ import annotations

import logging
from typing import List, Optional, Set

from cronwatcher.alerting import Alert, AlertManager
from cronwatcher.heartbeat import HeartbeatTracker
from cronwatcher.job_dependency import DependencyGraph, DependencyViolation

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Checks whether a job's upstream dependencies have been seen recently."""

    def __init__(
        self,
        graph: DependencyGraph,
        tracker: HeartbeatTracker,
        alert_manager: AlertManager,
    ) -> None:
        self._graph = graph
        self._tracker = tracker
        self._alert_manager = alert_manager

    def _completed_jobs(self) -> Set[str]:
        """Return the set of jobs that have at least one recorded heartbeat."""
        return {
            name
            for name in self._tracker.all_jobs()
            if self._tracker.last_seen(name) is not None
        }

    def check(self, job_name: str) -> Optional[DependencyViolation]:
        """Check upstream deps for *job_name*; fire an alert if any are unmet.

        Returns the violation if one exists, otherwise None.
        """
        completed = self._completed_jobs()
        violation = self._graph.check_violations(job_name, completed)
        if violation:
            missing = ", ".join(violation.missing_upstream)
            alert = Alert(
                job_name=job_name,
                kind="dependency_violation",
                message=(
                    f"Job '{job_name}' cannot run: upstream jobs not completed: {missing}"
                ),
                last_seen=self._tracker.last_seen(job_name),
            )
            self._alert_manager.handle(alert)
            logger.warning("Dependency violation for %s: missing %s", job_name, missing)
        return violation

    def check_all(self) -> List[DependencyViolation]:
        """Check all jobs registered in the dependency graph."""
        violations: List[DependencyViolation] = []
        for job_name in self._graph.all_jobs():
            result = self.check(job_name)
            if result:
                violations.append(result)
        return violations
