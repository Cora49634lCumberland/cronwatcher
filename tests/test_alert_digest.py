"""Tests for AlertDigest and DigestReport."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_digest import AlertDigest, DigestReport
from cronwatcher.alerting import Alert


@pytest.fixture()
def notifier():
    m = MagicMock()
    m.send.return_value = True
    return m


@pytest.fixture()
def digest(notifier):
    return AlertDigest(notifiers=[notifier])


def _alert(job: str = "job_a", kind: str = "overdue") -> Alert:
    return Alert(job_name=job, kind=kind, message="test")


class TestDigestReport:
    def test_total_alerts_sums_batches(self):
        from cronwatcher.alert_aggregator import AlertBatch

        b1 = AlertBatch(kind="overdue")
        b1.add(_alert("a", "overdue"))
        b2 = AlertBatch(kind="silence")
        b2.add(_alert("b", "silence"))
        b2.add(_alert("c", "silence"))
        report = DigestReport(generated_at=datetime.now(timezone.utc), batches=[b1, b2])
        assert report.total_alerts == 3

    def test_str_contains_kind_and_jobs(self):
        from cronwatcher.alert_aggregator import AlertBatch

        b = AlertBatch(kind="drift")
        b.add(_alert("job_x", "drift"))
        report = DigestReport(generated_at=datetime.now(timezone.utc), batches=[b])
        text = str(report)
        assert "drift" in text
        assert "job_x" in text


class TestAlertDigest:
    def test_pending_count_increases_on_add(self, digest):
        assert digest.pending_count() == 0
        digest.add(_alert("a"))
        assert digest.pending_count() == 1
        digest.add(_alert("b"))
        assert digest.pending_count() == 2

    def test_flush_resets_pending_count(self, digest):
        digest.add(_alert("a"))
        digest.flush()
        assert digest.pending_count() == 0

    def test_flush_calls_notifier(self, digest, notifier):
        digest.add(_alert("a"))
        digest.flush()
        notifier.send.assert_called_once()

    def test_flush_empty_skips_notifier(self, digest, notifier):
        report = digest.flush()
        notifier.send.assert_not_called()
        assert report.total_alerts == 0

    def test_flush_returns_digest_report(self, digest):
        digest.add(_alert("a"))
        report = digest.flush()
        assert isinstance(report, DigestReport)
        assert report.total_alerts == 1

    def test_alerts_grouped_by_kind(self, digest):
        digest.add(_alert("a", "overdue"))
        digest.add(_alert("b", "overdue"))
        digest.add(_alert("c", "silence"))
        report = digest.flush()
        kinds = {b.kind for b in report.batches}
        assert kinds == {"overdue", "silence"}

    def test_notifier_exception_does_not_raise(self, notifier):
        notifier.send.side_effect = RuntimeError("boom")
        d = AlertDigest(notifiers=[notifier])
        d.add(_alert("a"))
        # Should not propagate
        d.flush()
