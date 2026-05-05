"""Tests for cronwatcher.alerting."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.alerting import Alert, AlertManager
from cronwatcher.heartbeat import HeartbeatTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tracker() -> HeartbeatTracker:
    return HeartbeatTracker()


@pytest.fixture()
def manager(tracker: HeartbeatTracker) -> AlertManager:
    return AlertManager(tracker, handlers=[])


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------


class TestAlert:
    def test_str_with_last_seen(self) -> None:
        ts = datetime(2024, 1, 1, 12, 0, 0)
        alert = Alert(job_name="backup", message="overdue", severity="critical", last_seen=ts)
        result = str(alert)
        assert "[CRITICAL]" in result
        assert "backup" in result
        assert "2024-01-01T12:00:00" in result

    def test_str_never_seen(self) -> None:
        alert = Alert(job_name="sync", message="never run", severity="warning", last_seen=None)
        assert "never" in str(alert)


# ---------------------------------------------------------------------------
# AlertManager.check_all
# ---------------------------------------------------------------------------


class TestAlertManager:
    def test_no_alerts_when_no_jobs(self, manager: AlertManager) -> None:
        assert manager.check_all() == []

    def test_no_alert_for_healthy_job(self, tracker: HeartbeatTracker, manager: AlertManager) -> None:
        tracker.register("healthyjob", interval_seconds=300)
        tracker.record_execution("healthyjob")
        assert manager.check_all() == []

    def test_alert_fired_for_overdue_job(self, tracker: HeartbeatTracker, manager: AlertManager) -> None:
        tracker.register("slowjob", interval_seconds=60)
        # Manually backdate last_seen so the job appears overdue.
        tracker.jobs["slowjob"].last_seen = datetime.utcnow() - timedelta(seconds=120)
        alerts = manager.check_all()
        assert len(alerts) == 1
        assert alerts[0].job_name == "slowjob"

    def test_severity_critical_when_very_overdue(self, tracker: HeartbeatTracker, manager: AlertManager) -> None:
        tracker.register("latejob", interval_seconds=60)
        tracker.jobs["latejob"].last_seen = datetime.utcnow() - timedelta(seconds=300)
        alerts = manager.check_all()
        assert alerts[0].severity == "critical"

    def test_severity_warning_when_mildly_overdue(self, tracker: HeartbeatTracker, manager: AlertManager) -> None:
        tracker.register("mildjob", interval_seconds=60)
        tracker.jobs["mildjob"].last_seen = datetime.utcnow() - timedelta(seconds=90)
        alerts = manager.check_all()
        assert alerts[0].severity == "warning"

    def test_handler_called_on_alert(self, tracker: HeartbeatTracker) -> None:
        handler = MagicMock()
        mgr = AlertManager(tracker, handlers=[handler])
        tracker.register("failjob", interval_seconds=10)
        tracker.jobs["failjob"].last_seen = datetime.utcnow() - timedelta(seconds=60)
        mgr.check_all()
        handler.assert_called_once()
        called_alert = handler.call_args[0][0]
        assert isinstance(called_alert, Alert)

    def test_add_handler(self, manager: AlertManager) -> None:
        extra = MagicMock()
        manager.add_handler(extra)
        assert extra in manager.handlers

    def test_fired_state_cleared_after_recovery(self, tracker: HeartbeatTracker, manager: AlertManager) -> None:
        tracker.register("recoveryjob", interval_seconds=60)
        tracker.jobs["recoveryjob"].last_seen = datetime.utcnow() - timedelta(seconds=120)
        manager.check_all()  # fires alert
        assert "recoveryjob" in manager._fired
        # Simulate recovery
        tracker.record_execution("recoveryjob")
        manager.check_all()
        assert "recoveryjob" not in manager._fired
