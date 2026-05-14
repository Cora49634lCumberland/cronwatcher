"""Load WebhookDispatcher from configuration dictionaries or YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

from cronwatcher.webhook_config import _parse_single
from cronwatcher.webhook_dispatcher import WebhookDispatcher


def load_dispatcher_from_dict(config: Dict[str, Any]) -> WebhookDispatcher:
    """Build a WebhookDispatcher from a mapping.

    Accepted shapes::

        {"webhooks": [{"url": "...", "timeout": 5}, ...]}
        {"webhook": {"url": "..."}}
    """
    notifiers = []
    
    if "webhooks" in config:
        for entry in config["webhooks"]:
            notifiers.append(_parse_single(entry))
    elif "webhook" in config:
        notifiers.append(_parse_single(config["webhook"]))

    return WebhookDispatcher(notifiers=notifiers)


def load_dispatcher_from_yaml(path: str | Path) -> WebhookDispatcher:
    """Load a WebhookDispatcher from a YAML file."""
    if yaml is None:  # pragma: no cover
        raise ImportError("PyYAML is required to load dispatcher from YAML.")

    with open(path, "r", encoding="utf-8") as fh:
        data: Dict[str, Any] = yaml.safe_load(fh) or {}

    return load_dispatcher_from_dict(data)
