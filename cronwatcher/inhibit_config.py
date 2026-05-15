"""Load inhibition rules from config dicts or YAML files."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml

from cronwatcher.job_inhibitor import JobInhibitor


def load_inhibitions_from_dict(
    config: Dict[str, Any],
    inhibitor: Optional[JobInhibitor] = None,
) -> JobInhibitor:
    """Populate a :class:`JobInhibitor` from a config dictionary.

    Expected shape::

        inhibitions:
          - job: nightly_backup
            reason: "scheduled maintenance"
            duration_seconds: 3600   # optional; omit for indefinite
          - job: hourly_sync
            reason: "deploy in progress"
    """
    if inhibitor is None:
        inhibitor = JobInhibitor()

    rules: List[Dict[str, Any]] = config.get("inhibitions", [])
    if not isinstance(rules, list):
        raise ValueError("'inhibitions' must be a list of rule objects")

    for rule in rules:
        job_name: str = rule.get("job", "").strip()
        if not job_name:
            raise ValueError(f"Each inhibition rule must specify a non-empty 'job': {rule}")
        reason: str = str(rule.get("reason", "no reason given"))
        duration: Optional[float] = rule.get("duration_seconds")
        if duration is not None:
            duration = float(duration)
            if duration <= 0:
                raise ValueError(
                    f"duration_seconds must be positive for job {job_name!r}, got {duration}"
                )
        inhibitor.inhibit(job_name, reason=reason, duration_seconds=duration)

    return inhibitor


def load_inhibitions_from_yaml(
    path: str,
    inhibitor: Optional[JobInhibitor] = None,
) -> JobInhibitor:
    """Load inhibition rules from a YAML file at *path*."""
    with open(path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    return load_inhibitions_from_dict(config, inhibitor=inhibitor)
