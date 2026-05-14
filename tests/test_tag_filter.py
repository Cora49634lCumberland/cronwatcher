"""Tests for cronwatcher.tag_filter."""
from __future__ import annotations

import pytest

from cronwatcher.tag_filter import TagFilter, TagIndex


@pytest.fixture()
def index() -> TagIndex:
    idx = TagIndex()
    idx.add("backup", ["infra", "nightly"])
    idx.add("report", ["infra", "daily"])
    idx.add("cleanup", ["nightly", "daily"])
    idx.add("ping", ["infra"])
    return idx


@pytest.fixture()
def tag_filter(index: TagIndex) -> TagFilter:
    return TagFilter(index)


ALL_JOBS = ["backup", "report", "cleanup", "ping"]


class TestTagIndex:
    def test_jobs_for_tag(self, index: TagIndex) -> None:
        assert index.jobs_for_tag("infra") == {"backup", "report", "ping"}

    def test_jobs_for_unknown_tag(self, index: TagIndex) -> None:
        assert index.jobs_for_tag("unknown") == set()

    def test_tags_for_job(self, index: TagIndex) -> None:
        assert index.tags_for_job("backup") == {"infra", "nightly"}

    def test_all_tags_sorted(self, index: TagIndex) -> None:
        assert index.all_tags() == ["daily", "infra", "nightly"]

    def test_remove_job(self, index: TagIndex) -> None:
        index.remove("ping")
        assert "ping" not in index.jobs_for_tag("infra")

    def test_add_duplicate_tag_is_idempotent(self, index: TagIndex) -> None:
        index.add("backup", ["infra"])
        assert index.jobs_for_tag("infra") == {"backup", "report", "ping"}


class TestTagFilterMatchAny:
    def test_match_any_single_tag(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_any(ALL_JOBS, ["nightly"])
        assert sorted(result) == ["backup", "cleanup"]

    def test_match_any_multiple_tags(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_any(ALL_JOBS, ["nightly", "daily"])
        assert sorted(result) == ["backup", "cleanup", "report"]

    def test_match_any_unknown_tag_returns_empty(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_any(ALL_JOBS, ["ghost"])
        assert result == []

    def test_match_any_preserves_input_order(self, tag_filter: TagFilter) -> None:
        ordered = ["ping", "backup", "cleanup", "report"]
        result = tag_filter.match_any(ordered, ["nightly"])
        assert result == ["backup", "cleanup"]


class TestTagFilterMatchAll:
    def test_match_all_two_tags(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_all(ALL_JOBS, ["infra", "nightly"])
        assert result == ["backup"]

    def test_match_all_empty_tags_returns_all(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_all(ALL_JOBS, [])
        assert result == ALL_JOBS

    def test_match_all_impossible_combination(self, tag_filter: TagFilter) -> None:
        result = tag_filter.match_all(ALL_JOBS, ["infra", "daily", "nightly"])
        assert result == []


class TestTagFilterExclude:
    def test_exclude_single_tag(self, tag_filter: TagFilter) -> None:
        result = tag_filter.exclude(ALL_JOBS, ["infra"])
        assert result == ["cleanup"]

    def test_exclude_multiple_tags(self, tag_filter: TagFilter) -> None:
        result = tag_filter.exclude(ALL_JOBS, ["nightly", "daily"])
        assert result == ["ping"]

    def test_exclude_unknown_tag_keeps_all(self, tag_filter: TagFilter) -> None:
        result = tag_filter.exclude(ALL_JOBS, ["ghost"])
        assert result == ALL_JOBS
