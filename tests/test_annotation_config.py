"""Tests for cronwatcher.annotation_config."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.annotation_config import (
    load_annotations_from_dict,
    load_annotations_from_yaml,
)


class TestLoadAnnotationsFromDict:
    def test_empty_config_returns_empty_store(self) -> None:
        store = load_annotations_from_dict({})
        assert store.get_all("any_job") == {}

    def test_single_job_annotations(self) -> None:
        cfg = {"annotations": {"backup": {"owner": "ops", "priority": "high"}}}
        store = load_annotations_from_dict(cfg)
        assert store.get("backup", "owner") == "ops"
        assert store.get("backup", "priority") == "high"

    def test_multiple_jobs(self) -> None:
        cfg = {
            "annotations": {
                "job_a": {"team": "sre"},
                "job_b": {"team": "data", "env": "prod"},
            }
        }
        store = load_annotations_from_dict(cfg)
        assert store.get("job_a", "team") == "sre"
        assert store.get("job_b", "env") == "prod"

    def test_values_are_coerced_to_str(self) -> None:
        cfg = {"annotations": {"job_a": {"retries": 3}}}
        store = load_annotations_from_dict(cfg)
        assert store.get("job_a", "retries") == "3"

    def test_invalid_annotations_type_raises(self) -> None:
        with pytest.raises(ValueError, match="mapping"):
            load_annotations_from_dict({"annotations": ["not", "a", "dict"]})

    def test_invalid_job_annotations_type_raises(self) -> None:
        with pytest.raises(ValueError, match="key-value mapping"):
            load_annotations_from_dict({"annotations": {"job_a": "bad"}})


class TestLoadAnnotationsFromYaml:
    def test_load_from_yaml_file(self, tmp_path: Path) -> None:
        yaml_content = textwrap.dedent("""
            annotations:
              nightly_backup:
                owner: ops
                sla: 4h
        """)
        p = tmp_path / "annotations.yaml"
        p.write_text(yaml_content)
        store = load_annotations_from_yaml(str(p))
        assert store.get("nightly_backup", "owner") == "ops"
        assert store.get("nightly_backup", "sla") == "4h"

    def test_empty_yaml_returns_empty_store(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.yaml"
        p.write_text("")
        store = load_annotations_from_yaml(str(p))
        assert store.get_all("any") == {}
