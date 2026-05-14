"""Tests for cronwatcher.job_tagger.JobTagger."""
from __future__ import annotations

import pytest

from cronwatcher.job_registry import JobRegistry
from cronwatcher.job_tagger import JobTagger


@pytest.fixture()
def registry() -> JobRegistry:
    reg = JobRegistry()
    reg.register("backup", expression="0 2 * * *", timeout_seconds=300)
    reg.register("report", expression="0 6 * * *", timeout_seconds=120)
    reg.register("cleanup", expression="0 3 * * *", timeout_seconds=60)
    return reg


@pytest.fixture()
def tagger(registry: JobRegistry) -> JobTagger:
    jt = JobTagger(registry)
    jt.tag_job("backup", ["infra", "nightly"])
    jt.tag_job("report", ["infra", "daily"])
    jt.tag_job("cleanup", ["nightly", "daily"])
    return jt


class TestJobTagger:
    def test_tags_for_job_returns_assigned_tags(self, tagger: JobTagger) -> None:
        assert tagger.tags_for_job("backup") == {"infra", "nightly"}

    def test_tags_for_untagged_job_is_empty(self, tagger: JobTagger) -> None:
        assert tagger.tags_for_job("cleanup") == {"nightly", "daily"}

    def test_tag_unknown_job_raises(self, registry: JobRegistry) -> None:
        jt = JobTagger(registry)
        with pytest.raises(KeyError):
            jt.tag_job("ghost", ["infra"])

    def test_jobs_with_any_single_tag(self, tagger: JobTagger) -> None:
        result = tagger.jobs_with_any("nightly")
        assert sorted(result) == ["backup", "cleanup"]

    def test_jobs_with_any_multiple_tags(self, tagger: JobTagger) -> None:
        result = tagger.jobs_with_any("nightly", "daily")
        assert sorted(result) == ["backup", "cleanup", "report"]

    def test_jobs_with_all_intersection(self, tagger: JobTagger) -> None:
        result = tagger.jobs_with_all("infra", "nightly")
        assert result == ["backup"]

    def test_jobs_with_all_empty_tags_returns_all(self, tagger: JobTagger) -> None:
        all_names = tagger._registry.all_names()
        result = tagger.jobs_with_all()
        assert sorted(result) == sorted(all_names)

    def test_jobs_excluding_removes_tagged(self, tagger: JobTagger) -> None:
        result = tagger.jobs_excluding("infra", "nightly", "daily")
        assert result == []

    def test_jobs_excluding_unknown_tag_returns_all(self, tagger: JobTagger) -> None:
        all_names = sorted(tagger._registry.all_names())
        result = sorted(tagger.jobs_excluding("ghost"))
        assert result == all_names

    def test_untag_job_removes_associations(self, tagger: JobTagger) -> None:
        tagger.untag_job("backup")
        assert tagger.tags_for_job("backup") == set()
        assert "backup" not in tagger.jobs_with_any("infra")

    def test_all_tags_sorted(self, tagger: JobTagger) -> None:
        assert tagger.all_tags() == ["daily", "infra", "nightly"]

    def test_retag_job_adds_new_tags(self, tagger: JobTagger) -> None:
        tagger.tag_job("backup", ["critical"])
        assert "critical" in tagger.tags_for_job("backup")
        assert "infra" in tagger.tags_for_job("backup")
