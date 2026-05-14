"""Load AlertDigest and DigestScheduler from a config dict or YAML file."""

from __future__ import annotations

from typing import Any, Dict

import yaml

from cronwatcher.alert_digest import AlertDigest
from cronwatcher.digest_scheduler import DigestScheduler
from cronwatcher.notifier import LogNotifier
from cronwatcher.webhook_config import load_webhook_notifiers

_DEFAULT_INTERVAL = 300.0
_DEFAULT_LOG_LEVEL = "warning"


def load_digest_from_dict(cfg: Dict[str, Any]) -> DigestScheduler:
    """Build a DigestScheduler from a plain-dict config section.

    Expected shape::

        digest:
          interval_seconds: 300
          log_notifier:
            level: info
          webhooks:
            - url: https://hooks.example.com/...
    """
    digest_cfg = cfg.get("digest", {})
    interval = float(digest_cfg.get("interval_seconds", _DEFAULT_INTERVAL))

    notifiers = []

    log_cfg = digest_cfg.get("log_notifier")
    if log_cfg is not None:
        level = log_cfg.get("level", _DEFAULT_LOG_LEVEL) if isinstance(log_cfg, dict) else _DEFAULT_LOG_LEVEL
        notifiers.append(LogNotifier(level=level))
    else:
        # Always include a default log notifier
        notifiers.append(LogNotifier(level=_DEFAULT_LOG_LEVEL))

    webhook_notifiers = load_webhook_notifiers(digest_cfg)
    notifiers.extend(webhook_notifiers)

    digest = AlertDigest(notifiers=notifiers)
    return DigestScheduler(digest=digest, interval_seconds=interval)


def load_digest_from_yaml(path: str) -> DigestScheduler:
    """Convenience wrapper that reads a YAML file then calls load_digest_from_dict."""
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return load_digest_from_dict(cfg)
