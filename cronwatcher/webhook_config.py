"""Helpers to build WebhookNotifier instances from config dicts / YAML."""

from __future__ import annotations

from typing import Any, Dict, List

from cronwatcher.webhook_notifier import WebhookNotifier


def _parse_single(entry: Dict[str, Any]) -> WebhookNotifier:
    """Create a WebhookNotifier from a single config mapping.

    Expected keys:
        url (required): webhook endpoint
        timeout (optional, default 10): request timeout in seconds
        headers (optional): dict of extra HTTP headers
    """
    url = entry["url"]
    timeout = int(entry.get("timeout", 10))
    headers: Dict[str, str] = entry.get("headers") or {}
    return WebhookNotifier(url=url, timeout=timeout, extra_headers=headers)


def load_webhook_notifiers(config: Dict[str, Any]) -> List[WebhookNotifier]:
    """Return a list of WebhookNotifier instances from the top-level config dict.

    Supports two shapes:
      - ``webhooks: [...]``  — a list of webhook entries
      - ``webhook: {...}``   — a single webhook entry
    """
    notifiers: List[WebhookNotifier] = []

    if "webhooks" in config:
        for entry in config["webhooks"]:
            notifiers.append(_parse_single(entry))
    elif "webhook" in config:
        notifiers.append(_parse_single(config["webhook"]))

    return notifiers


def load_webhook_notifiers_from_yaml(path: str) -> List[WebhookNotifier]:
    """Load webhook notifiers from a YAML file at *path*."""
    import yaml  # optional dependency kept local

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return load_webhook_notifiers(data)
