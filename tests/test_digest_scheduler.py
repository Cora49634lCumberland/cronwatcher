"""Tests for DigestScheduler."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alert_digest import AlertDigest, DigestReport
from cronwatcher.alerting import Alert
from cronwatcher.digest_scheduler import DigestScheduler


@pytest.fixture()
def mock_digest():
    d = MagicMock(spec=AlertDigest)
    d.flush.return_value = MagicMock(spec=DigestReport, total_alerts=0)
    return d


class TestDigestScheduler:
    def test_invalid_interval_raises(self, mock_digest):
        with pytest.raises(ValueError):
            DigestScheduler(digest=mock_digest, interval_seconds=0)

    def test_negative_interval_raises(self, mock_digest):
        with pytest.raises(ValueError):
            DigestScheduler(digest=mock_digest, interval_seconds=-10)

    def test_last_report_initially_none(self, mock_digest):
        sched = DigestScheduler(digest=mock_digest, interval_seconds=60)
        assert sched.last_report is None

    def test_start_spawns_daemon_thread(self, mock_digest):
        sched = DigestScheduler(digest=mock_digest, interval_seconds=60)
        sched.start()
        assert sched._thread is not None
        assert sched._thread.is_alive()
        sched.stop()

    def test_stop_triggers_final_flush(self, mock_digest):
        sched = DigestScheduler(digest=mock_digest, interval_seconds=60)
        sched.start()
        sched.stop(timeout=2.0)
        # Final flush called during stop
        mock_digest.flush.assert_called()

    def test_double_start_is_safe(self, mock_digest):
        sched = DigestScheduler(digest=mock_digest, interval_seconds=60)
        sched.start()
        sched.start()  # second call should be a no-op
        assert sched._thread.is_alive()
        sched.stop()

    def test_flush_exception_does_not_crash_thread(self):
        real_digest = MagicMock(spec=AlertDigest)
        real_digest.flush.side_effect = RuntimeError("unexpected")
        sched = DigestScheduler(digest=real_digest, interval_seconds=60)
        sched.start()
        time.sleep(0.05)
        # Thread should still be alive despite flush error
        assert sched._thread.is_alive()
        sched.stop()
