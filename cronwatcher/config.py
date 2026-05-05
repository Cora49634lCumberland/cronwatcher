"""Configuration loader for cronwatcher.

Loads job definitions from a YAML/dict config and populates a
ScheduleRegistry so the rest of the system has a single source of truth.

Expected config shape (YAML example)::

    jobs:
      - name: backup
        schedule: "0 2 * * *"
        description: "Nightly backup"
        tolerance_seconds: 300
      - name: heartbeat
        schedule: "* * * * *"
"""

from __future__ import annotations

from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from cronwatcher.scheduler import CronSchedule, ScheduleRegistry


DEFAULT_TOLERANCE_SECONDS = 60


def load_from_dict(config: dict[str, Any]) -> ScheduleRegistry:
    """Build a ScheduleRegistry from a plain Python dict.

    Args:
        config: Mapping with a top-level ``jobs`` list.

    Returns:
        Populated :class:`ScheduleRegistry`.

    Raises:
        KeyError: If a job entry is missing required fields.
        ValueError: If a cron expression is invalid.
    """
    registry = ScheduleRegistry()
    jobs = config.get("jobs", [])
    for entry in jobs:
        schedule = CronSchedule(
            job_name=entry["name"],
            expression=entry["schedule"],
            description=entry.get("description", ""),
            tolerance_seconds=int(
                entry.get("tolerance_seconds", DEFAULT_TOLERANCE_SECONDS)
            ),
        )
        registry.register(schedule)
    return registry


def load_from_yaml(path: str) -> ScheduleRegistry:
    """Load configuration from a YAML file.

    Args:
        path: Filesystem path to the YAML config file.

    Returns:
        Populated :class:`ScheduleRegistry`.

    Raises:
        ImportError: If PyYAML is not installed.
        FileNotFoundError: If *path* does not exist.
    """
    if yaml is None:  # pragma: no cover
        raise ImportError("PyYAML is required: pip install pyyaml")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return load_from_dict(data)
