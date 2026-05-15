"""Tests for cronwatcher.job_annotations.AnnotationStore."""
from __future__ import annotations

import pytest

from cronwatcher.job_annotations import AnnotationStore


@pytest.fixture()
def store() -> AnnotationStore:
    return AnnotationStore()


class TestAnnotationStore:
    def test_set_and_get(self, store: AnnotationStore) -> None:
        store.set("job_a", "owner", "ops")
        assert store.get("job_a", "owner") == "ops"

    def test_get_missing_key_returns_none(self, store: AnnotationStore) -> None:
        assert store.get("job_a", "missing") is None

    def test_get_unknown_job_returns_none(self, store: AnnotationStore) -> None:
        assert store.get("unknown", "owner") is None

    def test_overwrite_annotation(self, store: AnnotationStore) -> None:
        store.set("job_a", "owner", "ops")
        store.set("job_a", "owner", "sre")
        assert store.get("job_a", "owner") == "sre"

    def test_get_all_returns_copy(self, store: AnnotationStore) -> None:
        store.set("job_a", "k1", "v1")
        store.set("job_a", "k2", "v2")
        result = store.get_all("job_a")
        assert result == {"k1": "v1", "k2": "v2"}
        # mutating the returned dict must not affect the store
        result["k1"] = "changed"
        assert store.get("job_a", "k1") == "v1"

    def test_get_all_unknown_job_is_empty(self, store: AnnotationStore) -> None:
        assert store.get_all("no_such_job") == {}

    def test_remove_existing_key(self, store: AnnotationStore) -> None:
        store.set("job_a", "owner", "ops")
        removed = store.remove("job_a", "owner")
        assert removed is True
        assert store.get("job_a", "owner") is None

    def test_remove_cleans_empty_job_entry(self, store: AnnotationStore) -> None:
        store.set("job_a", "owner", "ops")
        store.remove("job_a", "owner")
        assert store.get_all("job_a") == {}

    def test_remove_missing_key_returns_false(self, store: AnnotationStore) -> None:
        assert store.remove("job_a", "nonexistent") is False

    def test_remove_unknown_job_returns_false(self, store: AnnotationStore) -> None:
        assert store.remove("unknown", "owner") is False

    def test_clear_removes_all_annotations(self, store: AnnotationStore) -> None:
        store.set("job_a", "k1", "v1")
        store.set("job_a", "k2", "v2")
        store.clear("job_a")
        assert store.get_all("job_a") == {}

    def test_clear_unknown_job_is_noop(self, store: AnnotationStore) -> None:
        store.clear("ghost")  # should not raise

    def test_jobs_with_annotation_yields_matching(self, store: AnnotationStore) -> None:
        store.set("job_a", "owner", "ops")
        store.set("job_b", "owner", "sre")
        store.set("job_c", "priority", "high")
        result = set(store.jobs_with_annotation("owner"))
        assert result == {"job_a", "job_b"}

    def test_jobs_with_annotation_no_matches(self, store: AnnotationStore) -> None:
        store.set("job_a", "priority", "low")
        assert list(store.jobs_with_annotation("owner")) == []
