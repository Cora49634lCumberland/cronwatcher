"""Tests for cronwatcher.job_inhibitor."""

from __future__ import annotations

import time

import pytest

from cronwatcher.job_inhibitor import InhibitEntry, JobInhibitor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def inhibitor() -> JobInhibitor:
    return JobInhibitor()


# ---------------------------------------------------------------------------
# InhibitEntry tests
# ---------------------------------------------------------------------------


class TestInhibitEntry:
    def test_active_when_no_expiry(self):
        entry = InhibitEntry(job_name="backup", reason="maintenance")
        assert entry.is_active() is True

    def test_active_before_expiry(self):
        future = time.time() + 3600
        entry = InhibitEntry(job_name="backup", reason="deploy", expires_at=future)
        assert entry.is_active() is True

    def test_inactive_after_expiry(self):
        past = time.time() - 1
        entry = InhibitEntry(job_name="backup", reason="deploy", expires_at=past)
        assert entry.is_active() is False

    def test_seconds_remaining_none_for_indefinite(self):
        entry = InhibitEntry(job_name="backup", reason="x")
        assert entry.seconds_remaining() is None

    def test_seconds_remaining_positive_before_expiry(self):
        future = time.time() + 100
        entry = InhibitEntry(job_name="backup", reason="x", expires_at=future)
        remaining = entry.seconds_remaining()
        assert remaining is not None
        assert 90 < remaining <= 100

    def test_seconds_remaining_zero_when_expired(self):
        past = time.time() - 10
        entry = InhibitEntry(job_name="backup", reason="x", expires_at=past)
        assert entry.seconds_remaining() == 0.0

    def test_repr_contains_job_and_reason(self):
        entry = InhibitEntry(job_name="sync", reason="planned")
        r = repr(entry)
        assert "sync" in r
        assert "planned" in r


# ---------------------------------------------------------------------------
# JobInhibitor tests
# ---------------------------------------------------------------------------


class TestJobInhibitor:
    def test_not_inhibited_initially(self, inhibitor):
        assert inhibitor.is_inhibited("nightly") is False

    def test_inhibit_makes_job_inhibited(self, inhibitor):
        inhibitor.inhibit("nightly", reason="maintenance")
        assert inhibitor.is_inhibited("nightly") is True

    def test_release_clears_inhibition(self, inhibitor):
        inhibitor.inhibit("nightly", reason="maintenance")
        released = inhibitor.release("nightly")
        assert released is True
        assert inhibitor.is_inhibited("nightly") is False

    def test_release_returns_false_when_not_inhibited(self, inhibitor):
        assert inhibitor.release("unknown") is False

    def test_timed_inhibition_expires(self, inhibitor):
        inhibitor.inhibit("hourly", reason="test", duration_seconds=0.01)
        time.sleep(0.05)
        assert inhibitor.is_inhibited("hourly") is False

    def test_active_inhibitions_excludes_expired(self, inhibitor):
        inhibitor.inhibit("job_a", reason="a", duration_seconds=0.01)
        inhibitor.inhibit("job_b", reason="b")
        time.sleep(0.05)
        active = inhibitor.active_inhibitions()
        assert "job_a" not in active
        assert "job_b" in active

    def test_len_reflects_active_count(self, inhibitor):
        inhibitor.inhibit("x", reason="r1")
        inhibitor.inhibit("y", reason="r2")
        assert len(inhibitor) == 2

    def test_inhibit_overwrites_existing(self, inhibitor):
        inhibitor.inhibit("job", reason="first")
        inhibitor.inhibit("job", reason="second")
        active = inhibitor.active_inhibitions()
        assert active["job"].reason == "second"
