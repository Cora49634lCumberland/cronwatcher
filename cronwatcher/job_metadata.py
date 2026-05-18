"""Job metadata store: arbitrary key-value pairs attached to job names.

Distinct from annotations (which are user-facing notes); metadata is
intended for internal runtime use (e.g. owner, team, sla_minutes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class JobMetadata:
    """All metadata entries for a single job."""

    job_name: str
    _data: Dict[str, Any] = field(default_factory=dict, repr=False)

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* for this job."""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if absent."""
        return self._data.get(key, default)

    def remove(self, key: str) -> bool:
        """Delete *key*. Returns True if the key existed."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def keys(self) -> Iterator[str]:
        return iter(self._data)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __repr__(self) -> str:  # pragma: no cover
        return f"JobMetadata(job={self.job_name!r}, data={self._data!r})"


class MetadataStore:
    """Registry-level container for per-job metadata."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobMetadata] = {}

    def _ensure(self, job_name: str) -> JobMetadata:
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetadata(job_name)
        return self._jobs[job_name]

    def set(self, job_name: str, key: str, value: Any) -> None:
        """Set *key* = *value* for *job_name*."""
        self._ensure(job_name).set(key, value)

    def get(self, job_name: str, key: str, default: Any = None) -> Any:
        """Return metadata value, or *default*."""
        if job_name not in self._jobs:
            return default
        return self._jobs[job_name].get(key, default)

    def get_all(self, job_name: str) -> Dict[str, Any]:
        """Return a copy of all metadata for *job_name*."""
        if job_name not in self._jobs:
            return {}
        return self._jobs[job_name].as_dict()

    def remove(self, job_name: str, key: str) -> bool:
        """Remove a single key. Returns True if it existed."""
        if job_name not in self._jobs:
            return False
        return self._jobs[job_name].remove(key)

    def known_jobs(self) -> list[str]:
        """Return job names that have at least one metadata entry."""
        return [name for name, md in self._jobs.items() if list(md.keys())]
