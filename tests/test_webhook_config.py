"""Tests for webhook_config helpers."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.webhook_config import load_webhook_notifiers, load_webhook_notifiers_from_yaml
from cronwatcher.webhook_notifier import WebhookNotifier


class TestLoadWebhookNotifiers:
    def test_empty_config_returns_empty_list(self):
        result = load_webhook_notifiers({})
        assert result == []

    def test_single_webhook_key(self):
        config = {"webhook": {"url": "https://example.com/hook"}}
        result = load_webhook_notifiers(config)
        assert len(result) == 1
        assert isinstance(result[0], WebhookNotifier)
        assert result[0].url == "https://example.com/hook"

    def test_webhooks_list_key(self):
        config = {
            "webhooks": [
                {"url": "https://a.example.com/hook"},
                {"url": "https://b.example.com/hook", "timeout": 5},
            ]
        }
        result = load_webhook_notifiers(config)
        assert len(result) == 2
        assert result[1].timeout == 5

    def test_default_timeout_is_ten(self):
        config = {"webhook": {"url": "https://example.com/hook"}}
        result = load_webhook_notifiers(config)
        assert result[0].timeout == 10

    def test_extra_headers_parsed(self):
        config = {
            "webhook": {
                "url": "https://example.com/hook",
                "headers": {"X-Token": "abc123"},
            }
        }
        result = load_webhook_notifiers(config)
        assert result[0].extra_headers == {"X-Token": "abc123"}

    def test_missing_url_raises_key_error(self):
        with pytest.raises(KeyError):
            load_webhook_notifiers({"webhook": {"timeout": 5}})


class TestLoadWebhookNotifiersFromYaml:
    def test_load_from_yaml_file(self, tmp_path: Path):
        yaml_content = textwrap.dedent("""
            webhooks:
              - url: https://hooks.example.com/one
                timeout: 7
              - url: https://hooks.example.com/two
                headers:
                  Authorization: Bearer secret
        """)
        yaml_file = tmp_path / "cronwatcher.yaml"
        yaml_file.write_text(yaml_content)

        pytest.importorskip("yaml")
        result = load_webhook_notifiers_from_yaml(str(yaml_file))

        assert len(result) == 2
        assert result[0].url == "https://hooks.example.com/one"
        assert result[0].timeout == 7
        assert result[1].extra_headers == {"Authorization": "Bearer secret"}
