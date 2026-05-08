"""Registry for tracking configured cron jobs and their schedules."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.scheduler import CronSchedule


@dataclass
class JobConfig:
    """Configuration for a single monitored cron job."""

    name: str
    expression: str
    grace_seconds: int = 60
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Job name must not be empty")
        if self.grace_seconds < 0:
            raise ValueError("grace_seconds must be non-negative")

    @property
    def schedule(self) -> CronSchedule:
        return CronSchedule(self.expression)


class JobRegistry:
    """Maintains the set of configured jobs available for monitoring."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobConfig] = {}

    def register(self, job: JobConfig) -> None:
        """Add or replace a job configuration."""
        if not isinstance(job, JobConfig):
            raise TypeError("Expected a JobConfig instance")
        self._jobs[job.name] = job

    def unregister(self, name: str) -> None:
        """Remove a job by name. Raises KeyError if not found."""
        if name not in self._jobs:
            raise KeyError(f"Job '{name}' not found in registry")
        del self._jobs[name]

    def get(self, name: str) -> Optional[JobConfig]:
        """Return a job config or None if not registered."""
        return self._jobs.get(name)

    def all_jobs(self) -> List[JobConfig]:
        """Return all registered job configs."""
        return list(self._jobs.values())

    def enabled_jobs(self) -> List[JobConfig]:
        """Return only enabled job configs."""
        return [j for j in self._jobs.values() if j.enabled]

    def names(self) -> List[str]:
        """Return all registered job names."""
        return list(self._jobs.keys())

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(self, name: str) -> bool:
        return name in self._jobs

    @classmethod
    def from_config_list(cls, job_dicts: List[dict]) -> "JobRegistry":
        """Build a registry from a list of job config dicts."""
        registry = cls()
        for d in job_dicts:
            job = JobConfig(
                name=d["name"],
                expression=d["expression"],
                grace_seconds=d.get("grace_seconds", 60),
                enabled=d.get("enabled", True),
                tags=d.get("tags", []),
            )
            registry.register(job)
        return registry
