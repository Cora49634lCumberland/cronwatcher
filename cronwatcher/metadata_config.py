"""Load job metadata from a plain dict or YAML file."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

from cronwatcher.job_metadata import MetadataStore


def load_metadata_from_dict(config: Dict[str, Any]) -> MetadataStore:
    """Build a :class:`MetadataStore` from a plain mapping.

    Expected shape::

        metadata:
          backup_job:
            owner: ops-team
            sla_minutes: 60
          report_job:
            owner: data-team

    The top-level ``metadata`` key is optional; the dict may be the
    inner mapping directly.
    """
    store = MetadataStore()
    raw = config.get("metadata", config)
    if not isinstance(raw, dict):
        return store
    for job_name, entries in raw.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            store.set(str(job_name), str(key), value)
    return store


def load_metadata_from_yaml(path: str | Path) -> MetadataStore:
    """Load metadata from a YAML file at *path*."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load metadata from YAML files.")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return load_metadata_from_dict(data)
