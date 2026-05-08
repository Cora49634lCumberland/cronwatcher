"""Tests for cronwatcher.job_registry."""

import pytest

from cronwatcher.job_registry import JobConfig, JobRegistry
from cronwatcher.scheduler import CronSchedule


@pytest.fixture
def registry() -> JobRegistry:
    return JobRegistry()


@pytest.fixture
def daily_job() -> JobConfig:
    return JobConfig(name="daily_backup", expression="0 2 * * *", grace_seconds=120)


@pytest.fixture
def hourly_job() -> JobConfig:
    return JobConfig(name="hourly_sync", expression="0 * * * *", tags=["sync"])


class TestJobConfig:
    def test_schedule_returns_cron_schedule(self, daily_job):
        assert isinstance(daily_job.schedule, CronSchedule)

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            JobConfig(name="", expression="* * * * *")

    def test_negative_grace_raises(self):
        with pytest.raises(ValueError, match="grace_seconds"):
            JobConfig(name="job", expression="* * * * *", grace_seconds=-1)

    def test_default_enabled_is_true(self):
        job = JobConfig(name="j", expression="* * * * *")
        assert job.enabled is True

    def test_default_tags_empty(self):
        job = JobConfig(name="j", expression="* * * * *")
        assert job.tags == []


class TestJobRegistry:
    def test_register_and_get(self, registry, daily_job):
        registry.register(daily_job)
        result = registry.get("daily_backup")
        assert result is daily_job

    def test_get_unknown_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_len(self, registry, daily_job, hourly_job):
        registry.register(daily_job)
        registry.register(hourly_job)
        assert len(registry) == 2

    def test_contains(self, registry, daily_job):
        registry.register(daily_job)
        assert "daily_backup" in registry
        assert "missing" not in registry

    def test_unregister(self, registry, daily_job):
        registry.register(daily_job)
        registry.unregister("daily_backup")
        assert registry.get("daily_backup") is None

    def test_unregister_missing_raises(self, registry):
        with pytest.raises(KeyError):
            registry.unregister("ghost")

    def test_register_replaces_existing(self, registry, daily_job):
        registry.register(daily_job)
        updated = JobConfig(name="daily_backup", expression="0 3 * * *")
        registry.register(updated)
        assert registry.get("daily_backup").expression == "0 3 * * *"

    def test_all_jobs(self, registry, daily_job, hourly_job):
        registry.register(daily_job)
        registry.register(hourly_job)
        names = {j.name for j in registry.all_jobs()}
        assert names == {"daily_backup", "hourly_sync"}

    def test_enabled_jobs_filters_disabled(self, registry):
        registry.register(JobConfig(name="active", expression="* * * * *", enabled=True))
        registry.register(JobConfig(name="inactive", expression="* * * * *", enabled=False))
        enabled = registry.enabled_jobs()
        assert len(enabled) == 1
        assert enabled[0].name == "active"

    def test_names(self, registry, daily_job, hourly_job):
        registry.register(daily_job)
        registry.register(hourly_job)
        assert set(registry.names()) == {"daily_backup", "hourly_sync"}

    def test_register_wrong_type_raises(self, registry):
        with pytest.raises(TypeError):
            registry.register({"name": "bad"})

    def test_from_config_list(self):
        data = [
            {"name": "job_a", "expression": "* * * * *", "grace_seconds": 30, "tags": ["prod"]},
            {"name": "job_b", "expression": "0 * * * *"},
        ]
        reg = JobRegistry.from_config_list(data)
        assert len(reg) == 2
        assert reg.get("job_a").grace_seconds == 30
        assert reg.get("job_a").tags == ["prod"]
        assert reg.get("job_b").grace_seconds == 60
