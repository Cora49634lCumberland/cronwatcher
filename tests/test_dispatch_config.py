"""Tests for dispatch_config loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.dispatch_config import load_dispatcher_from_dict, load_dispatcher_from_yaml
from cronwatcher.webhook_dispatcher import WebhookDispatcher


class TestLoadDispatcherFromDict:
    def test_empty_config_returns_empty_dispatcher(self):
        d = load_dispatcher_from_dict({})
        assert isinstance(d, WebhookDispatcher)
        # dispatching to zero notifiers
        from cronwatcher.alerting import Alert
        result = d.dispatch(Alert(job_name="x", message="y"))
        assert result.total == 0

    def test_single_webhook_key(self):
        cfg = {"webhook": {"url": "https://example.com/hook"}}
        d = load_dispatcher_from_dict(cfg)
        assert len(d._notifiers) == 1
        assert d._notifiers[0].url == "https://example.com/hook"

    def test_webhooks_list_key(self):
        cfg = {
            "webhooks": [
                {"url": "https://example.com/a"},
                {"url": "https://example.com/b", "timeout": 3},
            ]
        }
        d = load_dispatcher_from_dict(cfg)
        assert len(d._notifiers) == 2
        assert d._notifiers[1].timeout == 3

    def test_default_timeout_applied(self):
        cfg = {"webhook": {"url": "https://example.com/hook"}}
        d = load_dispatcher_from_dict(cfg)
        assert d._notifiers[0].timeout == 10


class TestLoadDispatcherFromYaml:
    def test_loads_from_yaml_file(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""
            webhooks:
              - url: https://hooks.example.com/one
                timeout: 5
              - url: https://hooks.example.com/two
        """)
        p = tmp_path / "dispatch.yaml"
        p.write_text(yaml_content)

        d = load_dispatcher_from_yaml(p)
        assert len(d._notifiers) == 2
        assert d._notifiers[0].timeout == 5
        assert d._notifiers[1].url == "https://hooks.example.com/two"

    def test_empty_yaml_returns_empty_dispatcher(self, tmp_path: Path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        d = load_dispatcher_from_yaml(p)
        assert len(d._notifiers) == 0
