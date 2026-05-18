"""Tests for cronwatcher.job_metadata and cronwatcher.metadata_config."""
from __future__ import annotations

import pytest

from cronwatcher.job_metadata import JobMetadata, MetadataStore
from cronwatcher.metadata_config import load_metadata_from_dict


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store() -> MetadataStore:
    return MetadataStore()


# ---------------------------------------------------------------------------
# JobMetadata unit tests
# ---------------------------------------------------------------------------

class TestJobMetadata:
    def test_set_and_get(self):
        md = JobMetadata("myjob")
        md.set("owner", "ops")
        assert md.get("owner") == "ops"

    def test_get_missing_returns_default(self):
        md = JobMetadata("myjob")
        assert md.get("missing") is None
        assert md.get("missing", "fallback") == "fallback"

    def test_remove_existing_key(self):
        md = JobMetadata("myjob")
        md.set("k", "v")
        result = md.remove("k")
        assert result is True
        assert md.get("k") is None

    def test_remove_missing_key_returns_false(self):
        md = JobMetadata("myjob")
        assert md.remove("nonexistent") is False

    def test_as_dict_returns_copy(self):
        md = JobMetadata("myjob")
        md.set("a", 1)
        d = md.as_dict()
        d["a"] = 999
        assert md.get("a") == 1

    def test_keys_iteration(self):
        md = JobMetadata("myjob")
        md.set("x", 1)
        md.set("y", 2)
        assert set(md.keys()) == {"x", "y"}


# ---------------------------------------------------------------------------
# MetadataStore unit tests
# ---------------------------------------------------------------------------

class TestMetadataStore:
    def test_set_and_get(self, store):
        store.set("job_a", "owner", "team-ops")
        assert store.get("job_a", "owner") == "team-ops"

    def test_get_unknown_job_returns_default(self, store):
        assert store.get("ghost", "owner") is None
        assert store.get("ghost", "owner", "nobody") == "nobody"

    def test_get_all_returns_all_keys(self, store):
        store.set("job_b", "owner", "data")
        store.set("job_b", "sla_minutes", 30)
        result = store.get_all("job_b")
        assert result == {"owner": "data", "sla_minutes": 30}

    def test_get_all_unknown_job_returns_empty(self, store):
        assert store.get_all("nobody") == {}

    def test_remove_key(self, store):
        store.set("job_c", "env", "prod")
        assert store.remove("job_c", "env") is True
        assert store.get("job_c", "env") is None

    def test_remove_unknown_job_returns_false(self, store):
        assert store.remove("ghost", "env") is False

    def test_known_jobs_excludes_empty(self, store):
        store.set("job_d", "k", "v")
        store.set("job_e", "k", "v")
        store.remove("job_e", "k")
        assert "job_d" in store.known_jobs()
        assert "job_e" not in store.known_jobs()


# ---------------------------------------------------------------------------
# load_metadata_from_dict tests
# ---------------------------------------------------------------------------

class TestLoadMetadataFromDict:
    def test_empty_config_returns_empty_store(self):
        s = load_metadata_from_dict({})
        assert s.get_all("anything") == {}

    def test_nested_under_metadata_key(self):
        cfg = {"metadata": {"backup": {"owner": "ops", "sla_minutes": 60}}}
        s = load_metadata_from_dict(cfg)
        assert s.get("backup", "owner") == "ops"
        assert s.get("backup", "sla_minutes") == 60

    def test_flat_dict_without_metadata_key(self):
        cfg = {"report": {"owner": "data-team"}}
        s = load_metadata_from_dict(cfg)
        assert s.get("report", "owner") == "data-team"

    def test_multiple_jobs(self):
        cfg = {
            "metadata": {
                "job_a": {"owner": "a"},
                "job_b": {"owner": "b"},
            }
        }
        s = load_metadata_from_dict(cfg)
        assert s.get("job_a", "owner") == "a"
        assert s.get("job_b", "owner") == "b"

    def test_non_dict_entries_are_skipped(self):
        cfg = {"metadata": {"bad_job": "not-a-dict"}}
        s = load_metadata_from_dict(cfg)
        assert s.get_all("bad_job") == {}
