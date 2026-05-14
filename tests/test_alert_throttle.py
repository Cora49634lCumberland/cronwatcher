"""Tests for cronwatcher.alert_throttle."""

import time
import pytest

from cronwatcher.alerting import Alert
from cronwatcher.alert_throttle import AlertThrottle, ThrottleEntry


@pytest.fixture
def alert() -> Alert:
    return Alert(job_name="backup", kind="overdue", message="backup is overdue")


@pytest.fixture
def throttle() -> AlertThrottle:
    return AlertThrottle(cooldown_seconds=60.0)


class TestThrottleEntry:
    def test_seconds_since_last_uses_now(self):
        now = time.time()
        entry = ThrottleEntry(
            job_name="j", alert_kind="overdue",
            first_sent_at=now - 90, last_sent_at=now - 90
        )
        assert entry.seconds_since_last(now) == pytest.approx(90, abs=1)

    def test_repr_contains_job_and_kind(self):
        entry = ThrottleEntry(
            job_name="myjob", alert_kind="silence",
            first_sent_at=0.0, last_sent_at=0.0
        )
        assert "myjob" in repr(entry)
        assert "silence" in repr(entry)


class TestAlertThrottle:
    def test_not_suppressed_initially(self, throttle, alert):
        assert throttle.is_suppressed(alert) is False

    def test_suppressed_after_record_sent(self, throttle, alert):
        now = time.time()
        throttle.record_sent(alert, now=now)
        assert throttle.is_suppressed(alert, now=now + 10) is True

    def test_not_suppressed_after_cooldown_expires(self, throttle, alert):
        now = time.time()
        throttle.record_sent(alert, now=now)
        assert throttle.is_suppressed(alert, now=now + 61) is False

    def test_exactly_at_cooldown_boundary_not_suppressed(self, throttle, alert):
        now = time.time()
        throttle.record_sent(alert, now=now)
        # exactly at cooldown: not strictly less than, so not suppressed
        assert throttle.is_suppressed(alert, now=now + 60.0) is False

    def test_record_sent_increments_count(self, throttle, alert):
        now = time.time()
        throttle.record_sent(alert, now=now)
        throttle.record_sent(alert, now=now + 70)  # after cooldown
        entry = throttle.entry_for("backup", "overdue")
        assert entry is not None
        assert entry.send_count == 2

    def test_first_sent_at_preserved_on_subsequent_sends(self, throttle, alert):
        now = time.time()
        throttle.record_sent(alert, now=now)
        throttle.record_sent(alert, now=now + 120)
        entry = throttle.entry_for("backup", "overdue")
        assert entry.first_sent_at == pytest.approx(now, abs=0.01)

    def test_reset_clears_specific_entry(self, throttle, alert):
        throttle.record_sent(alert)
        throttle.reset("backup", "overdue")
        assert throttle.is_suppressed(alert) is False
        assert throttle.entry_for("backup", "overdue") is None

    def test_reset_all_clears_everything(self, throttle, alert):
        other = Alert(job_name="sync", kind="silence", message="silent")
        throttle.record_sent(alert)
        throttle.record_sent(other)
        throttle.reset_all()
        assert throttle.is_suppressed(alert) is False
        assert throttle.is_suppressed(other) is False

    def test_different_jobs_tracked_independently(self, throttle):
        a1 = Alert(job_name="job_a", kind="overdue", message="")
        a2 = Alert(job_name="job_b", kind="overdue", message="")
        now = time.time()
        throttle.record_sent(a1, now=now)
        assert throttle.is_suppressed(a1, now=now + 5) is True
        assert throttle.is_suppressed(a2, now=now + 5) is False

    def test_negative_cooldown_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            AlertThrottle(cooldown_seconds=-1)

    def test_zero_cooldown_never_suppresses(self, alert):
        throttle = AlertThrottle(cooldown_seconds=0)
        now = time.time()
        throttle.record_sent(alert, now=now)
        assert throttle.is_suppressed(alert, now=now) is False
