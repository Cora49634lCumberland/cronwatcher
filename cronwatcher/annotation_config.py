"""Load job annotations from a config dict or YAML file."""
from __future__ import annotations

from typing import Any, Dict

import yaml

from cronwatcher.job_annotations import AnnotationStore


def load_annotations_from_dict(cfg: Dict[str, Any]) -> AnnotationStore:
    """Populate an AnnotationStore from a config mapping.

    Expected structure::

        annotations:
          backup_job:
            owner: "ops-team"
            priority: "high"
          report_job:
            owner: "data-team"
    """
    store = AnnotationStore()
    raw = cfg.get("annotations", {})
    if not isinstance(raw, dict):
        raise ValueError("'annotations' must be a mapping of job_name -> {key: value}")
    for job_name, pairs in raw.items():
        if not isinstance(pairs, dict):
            raise ValueError(
                f"Annotations for job '{job_name}' must be a key-value mapping, got {type(pairs).__name__}"
            )
        for key, value in pairs.items():
            store.set(str(job_name), str(key), str(value))
    return store


def load_annotations_from_yaml(path: str) -> AnnotationStore:
    """Load annotations from a YAML file at *path*."""
    with open(path, "r") as fh:
        cfg = yaml.safe_load(fh) or {}
    return load_annotations_from_dict(cfg)
