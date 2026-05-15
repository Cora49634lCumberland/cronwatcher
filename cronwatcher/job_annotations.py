"""Job annotation support: attach arbitrary key-value metadata to jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional


@dataclass
class AnnotationStore:
    """Stores key-value annotations keyed by job name."""

    _data: Dict[str, Dict[str, str]] = field(default_factory=dict, init=False, repr=False)

    def set(self, job_name: str, key: str, value: str) -> None:
        """Set or overwrite an annotation for a job."""
        self._data.setdefault(job_name, {})[key] = value

    def get(self, job_name: str, key: str) -> Optional[str]:
        """Return the annotation value, or None if not present."""
        return self._data.get(job_name, {}).get(key)

    def get_all(self, job_name: str) -> Dict[str, str]:
        """Return all annotations for a job (empty dict if none)."""
        return dict(self._data.get(job_name, {}))

    def remove(self, job_name: str, key: str) -> bool:
        """Remove a single annotation.  Returns True if it existed."""
        job_anns = self._data.get(job_name)
        if job_anns and key in job_anns:
            del job_anns[key]
            if not job_anns:
                del self._data[job_name]
            return True
        return False

    def clear(self, job_name: str) -> None:
        """Remove all annotations for a job."""
        self._data.pop(job_name, None)

    def jobs_with_annotation(self, key: str) -> Iterator[str]:
        """Yield job names that have a particular annotation key."""
        for job_name, anns in self._data.items():
            if key in anns:
                yield job_name

    def __repr__(self) -> str:  # pragma: no cover
        return f"AnnotationStore(jobs={list(self._data.keys())})"
