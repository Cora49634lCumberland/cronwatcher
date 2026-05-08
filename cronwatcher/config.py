"""Configuration loading for cronwatcher."""

from typing import Any, Dict, List

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False

from cronwatcher.job_registry import JobRegistry


def load_from_dict(data: Dict[str, Any]) -> JobRegistry:
    """Build a JobRegistry from a parsed configuration dictionary.

    Expected structure::

        jobs:
          - name: my_job
            expression: "* * * * *"
            grace_seconds: 60
            enabled: true
            tags:
              - production
    """
    if not isinstance(data, dict):
        raise TypeError("Configuration must be a mapping")

    raw_jobs: List[dict] = data.get("jobs", [])
    if not isinstance(raw_jobs, list):
        raise ValueError("'jobs' must be a list")

    return JobRegistry.from_config_list(raw_jobs)


def load_from_yaml(path: str) -> JobRegistry:
    """Load a JobRegistry from a YAML configuration file.

    Args:
        path: Filesystem path to the YAML config file.

    Returns:
        A populated JobRegistry.

    Raises:
        ImportError: If PyYAML is not installed.
        FileNotFoundError: If the path does not exist.
    """
    if not _YAML_AVAILABLE:  # pragma: no cover
        raise ImportError(
            "PyYAML is required to load YAML configs. "
            "Install it with: pip install pyyaml"
        )

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if data is None:
        data = {}

    return load_from_dict(data)
