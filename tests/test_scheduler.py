"""Tests for cronwatcher.scheduler."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from cronwatcher.scheduler import CronSchedule, ScheduleRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> ScheduleRegistry:
    return ScheduleRegistry()


@pytest.fixture
def every_minute() -> CronSchedule:
    return CronSchedule(job_name="heartbeat", expression="* * * * *", tolerance_seconds=30)


@pytest.fixture
def every_hour() -> CronSchedule:
    return CronSchedule(job_name="report", expression="0 * * * *", tolerance_seconds=120)


# ---------------------------------------------------------------------------
# CronSchedule tests
# ---------------------------------------------------------------------------

class TestCronSchedule:
    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronSchedule(job_name="bad", expression="not-a-cron")

    def test_expected_interval_every_minute(self, every_minute):
        interval = every_minute.expected_interval_seconds()
        assert interval == pytest.approx(60.0, abs=1)

    def test_expected_interval_every_hour(self, every_hour):
        interval = every_hour.expected_interval_seconds()
        assert interval == pytest.approx(3600.0, abs=1)

    def test_deadline_includes_tolerance(self, every_minute):
        deadline = every_minute.deadline_seconds()
        assert deadline == pytest.approx(90.0, abs=1)  # 60 + 30

    def test_next_run_is_in_the_future(self, every_minute):
        now = datetime.now(tz=timezone.utc)
        nxt = every_minute.next_run(after=now)
        assert nxt > now

    def test_next_run_after_given_time(self, every_hour):
        base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        nxt = every_hour.next_run(after=base)
        assert nxt.hour == 13
        assert nxt.minute == 0

    def test_description_defaults_empty(self, every_minute):
        assert every_minute.description == ""


# ---------------------------------------------------------------------------
# ScheduleRegistry tests
# ---------------------------------------------------------------------------

class TestScheduleRegistry:
    def test_register_and_get(self, registry, every_minute):
        registry.register(every_minute)
        assert registry.get("heartbeat") is every_minute

    def test_get_missing_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_len(self, registry, every_minute, every_hour):
        registry.register(every_minute)
        registry.register(every_hour)
        assert len(registry) == 2

    def test_all_schedules(self, registry, every_minute, every_hour):
        registry.register(every_minute)
        registry.register(every_hour)
        names = {s.job_name for s in registry.all_schedules()}
        assert names == {"heartbeat", "report"}

    def test_deadline_for_registered(self, registry, every_minute):
        registry.register(every_minute)
        deadline = registry.deadline_for("heartbeat")
        assert deadline == pytest.approx(90.0, abs=1)

    def test_deadline_for_missing_returns_none(self, registry):
        assert registry.deadline_for("ghost") is None

    def test_register_overwrites(self, registry):
        s1 = CronSchedule(job_name="job", expression="* * * * *")
        s2 = CronSchedule(job_name="job", expression="0 * * * *")
        registry.register(s1)
        registry.register(s2)
        assert registry.get("job").expression == "0 * * * *"
        assert len(registry) == 1
